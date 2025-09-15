import json
import os
import shutil
from celery import shared_task
from utils import COMFYUI_REPO_URL, create_symlink, create_virtualenv, install_default_custom_nodes, install_pip_reqs, normalize_model_filepaths_in_workflow_json, run_command, run_command_in_project_venv, set_default_workflow_from_launcher_json, set_launcher_state_data, setup_custom_nodes_from_snapshot, setup_files_from_launcher_json, setup_initial_models_folder, InstallationValidator, copy_workflow_assets
from progress_tracker import update_progress, add_log_entry
from auto_model_downloader import auto_download_models

# Import recovery components for Celery tasks
try:
    from .recovery import recoverable
    RECOVERY_AVAILABLE = True
except ImportError:
    RECOVERY_AVAILABLE = False

# Apply recovery decorator to create_comfyui_project if available
if RECOVERY_AVAILABLE:
    # For Celery tasks, we need to handle the bound task differently
    def recoverable_create_comfyui_project(self, *args, **kwargs):
        @recoverable(
            max_retries=3,
            initial_delay=10.0,
            backoff_factor=2.0,
            max_delay=1800.0,  # 30 minutes max delay
            timeout=7200.0,  # 2 hours timeout for full project creation
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=1800.0  # 30 minutes circuit breaker timeout
        )
        def wrapper(*args, **kwargs):
            # Original implementation
            return original_create_comfyui_project(self, *args, **kwargs)
        return wrapper(*args, **kwargs)
    
    # Store original task function
    original_create_comfyui_project = create_comfyui_project
    
    # Apply recovery wrapper
    def create_comfyui_project_with_recovery(self, *args, **kwargs):
        return recoverable_create_comfyui_project(self, *args, **kwargs)
    
    create_comfyui_project = create_comfyui_project_with_recovery

@shared_task(ignore_result=False, bind=True)
def create_comfyui_project(
    self, project_folder_path, models_folder_path, id, name, launcher_json=None, port=None, create_project_folder=True, pending_assets=None
):
    project_folder_path = os.path.abspath(project_folder_path)
    models_folder_path = os.path.abspath(models_folder_path)

    # Helper functions for progress and logging
    def log(level, message, extra_data=None):
        add_log_entry(id, level, message, extra_data)
    
    def progress(data):
        update_progress(id, data)
    
    try:
        if create_project_folder:
            assert not os.path.exists(project_folder_path), f"Project folder already exists at {project_folder_path}"
            os.makedirs(project_folder_path)
        else:
            assert os.path.exists(project_folder_path), f"Project folder does not exist at {project_folder_path}"
        
        log('info', f'Starting project creation for {name}')

        set_launcher_state_data(
            project_folder_path,
            {"id":id,"name":name, "status_message": "Downloading ComfyUI...", "state": "download_comfyui"},
        )
        progress({'stage': 'download_comfyui', 'progress': 0})
        log('info', 'Downloading ComfyUI from GitHub')
        
        # Modify the subprocess.run calls to capture and log the stdout
        run_command(
            ["git", "clone", COMFYUI_REPO_URL, os.path.join(project_folder_path, 'comfyui')],
            log_callback=log
        )
        
        progress({'stage': 'download_comfyui', 'progress': 100})
        log('info', 'ComfyUI downloaded successfully')

        if launcher_json:
            # Handle missing snapshot_json gracefully
            if "snapshot_json" in launcher_json and launcher_json["snapshot_json"]:
                comfyui_commit_hash = launcher_json["snapshot_json"].get("comfyui")
                if comfyui_commit_hash:
                    log('info', f'Checking out ComfyUI commit: {comfyui_commit_hash}')
                    run_command(
                        ["git", "checkout", comfyui_commit_hash],
                        cwd=os.path.join(project_folder_path, 'comfyui'),
                        log_callback=log
                    )
            # Ensure workflow_json exists before normalizing
            if 'workflow_json' in launcher_json and launcher_json['workflow_json']:
                launcher_json['workflow_json'] = normalize_model_filepaths_in_workflow_json(launcher_json['workflow_json'])
            else:
                log('warning', 'No workflow_json found in launcher_json')

        
        # move the comfyui/web/index.html file to comfyui/web/comfyui_index.html
        index_path = os.path.join(project_folder_path, "comfyui", "web", "index.html")
        if os.path.exists(index_path):
            os.rename(
                index_path,
                os.path.join(project_folder_path, "comfyui", "web", "comfyui_index.html"),
            )

        # copy the web/comfy_frame.html file to comfyui/web/index.html
        comfy_frame_path = os.path.join("server", "web", "comfy_frame.html")
        web_dir = os.path.join(project_folder_path, "comfyui", "web")
        if os.path.exists(comfy_frame_path) and os.path.exists(web_dir):
            shutil.copy(
                comfy_frame_path,
                os.path.join(web_dir, "index.html"),
            )

        # remove the models folder that exists in comfyui and symlink the shared_models folder as models
        if os.path.exists(os.path.join(project_folder_path, "comfyui", "models")):
            shutil.rmtree(
                os.path.join(project_folder_path, "comfyui", "models"), ignore_errors=True
            )

        if not os.path.exists(models_folder_path):
            setup_initial_models_folder(models_folder_path)

        # create a folder in project folder/comfyui/models that is a symlink to the models folder
        create_symlink(models_folder_path, os.path.join(project_folder_path, "comfyui", "models"))

        set_launcher_state_data(
            project_folder_path,
            {"status_message": "Installing ComfyUI...", "state": "install_comfyui"},
        )
        progress({'stage': 'install_comfyui', 'progress': 0})
        log('info', 'Installing ComfyUI dependencies')

        # create a new virtualenv in project folder/venv
        create_virtualenv(os.path.join(project_folder_path, 'venv'))

        # activate the virtualenv + install comfyui requirements
        run_command_in_project_venv(
            project_folder_path,
            f"pip install -r {os.path.join(project_folder_path, 'comfyui', 'requirements.txt')}",
        )
        progress({'stage': 'install_comfyui', 'progress': 100})
        log('info', 'ComfyUI dependencies installed')

        set_launcher_state_data(
            project_folder_path,
            {
                "status_message": "Installing custom nodes...",
                "state": "install_custom_nodes",
            },
        )
        progress({'stage': 'install_custom_nodes', 'progress': 0})
        log('info', 'Starting custom nodes installation')

        # install default custom nodes
        install_default_custom_nodes(project_folder_path, launcher_json)

        # Install custom nodes and track failures
        failed_custom_nodes = setup_custom_nodes_from_snapshot(
            project_folder_path, 
            launcher_json,
            progress_callback=progress,
            log_callback=log
        )
        
        if failed_custom_nodes:
            print(f"WARNING: {len(failed_custom_nodes)} custom nodes failed to install completely")
            log('warning', f'{len(failed_custom_nodes)} custom nodes failed to install', 
                {'failed_nodes': list(failed_custom_nodes)})

        # install pip requirements
        if launcher_json and "pip_requirements" in launcher_json:
            set_launcher_state_data(
                project_folder_path,
                {
                    "status_message": "Installing Python dependencies...",
                    "state": "install_pip_requirements",
                },
            )
            progress({'stage': 'pip_requirements', 'progress': 0})
            log('info', f'Installing {len(launcher_json["pip_requirements"])} Python dependencies')
            install_pip_reqs(project_folder_path, launcher_json["pip_requirements"])
            progress({'stage': 'pip_requirements', 'progress': 100})

        # download all necessary files
        set_launcher_state_data(
            project_folder_path,
            {
                "status_message": "Downloading models & other files...",
                "state": "download_files",
            },
        )
        progress({'stage': 'download_files', 'progress': 0})
        log('info', 'Starting model downloads')

        # Progress callback for file downloads
        def download_progress_callback(file_path, downloaded, total):
            if total > 0:
                percent = int((downloaded / total) * 100)
                filename = os.path.basename(file_path)
                set_launcher_state_data(
                    project_folder_path,
                    {
                        "status_message": f"Downloading {filename}: {percent}%",
                        "state": "download_files",
                        "download_progress": {
                            "current_file": filename,
                            "progress": percent
                        }
                    },
                )
                progress({
                    'stage': 'download_files',
                    'current_file': filename,
                    'file_progress': percent,
                    'downloaded': downloaded,
                    'total': total
                })
        
        failed_downloads = setup_files_from_launcher_json(project_folder_path, launcher_json, download_progress_callback)
        
        if failed_downloads:
            print(f"WARNING: {len(failed_downloads)} files failed to download")
            log('warning', f'{len(failed_downloads)} files failed to download', 
                {'failed_files': list(failed_downloads)})
            # Store failed downloads in launcher state for UI to display
            set_launcher_state_data(
                project_folder_path,
                {
                    "failed_downloads": list(failed_downloads),
                    "failed_custom_nodes": list(failed_custom_nodes) if failed_custom_nodes else []
                },
            )
        set_default_workflow_from_launcher_json(project_folder_path, launcher_json)

        if launcher_json:
            with open(os.path.join(project_folder_path, "launcher.json"), "w") as f:
                json.dump(launcher_json, f)

        if port is not None:
            with open(os.path.join(project_folder_path, "port.txt"), "w") as f:
                f.write(str(port))
        
        # Handle pending assets from ZIP import
        if pending_assets:
            set_launcher_state_data(
                project_folder_path,
                {
                    "status_message": "Copying workflow assets...",
                    "state": "copy_assets",
                },
            )
            progress({'stage': 'copy_assets', 'progress': 0})
            log('info', f'Copying {len(pending_assets.get("assets", {}))} workflow assets')
            
            try:
                # Copy assets to appropriate directories
                new_paths = copy_workflow_assets(pending_assets["assets"], project_folder_path)
                
                # Update workflow JSON with new asset paths if needed
                if new_paths and launcher_json:
                    workflow_json_str = json.dumps(launcher_json["workflow_json"])
                    for old_ref, new_ref in new_paths.items():
                        workflow_json_str = workflow_json_str.replace(old_ref, new_ref)
                    launcher_json["workflow_json"] = json.loads(workflow_json_str)
                    
                    # Save updated launcher.json
                    with open(os.path.join(project_folder_path, "launcher.json"), "w") as f:
                        json.dump(launcher_json, f)
                    
                    # Update default workflow
                    set_default_workflow_from_launcher_json(project_folder_path, launcher_json)
                
                progress({'stage': 'copy_assets', 'progress': 100})
                log('info', 'Assets copied successfully')
                
            except Exception as e:
                log('warning', f'Failed to copy some assets: {str(e)}')
            finally:
                # Clean up temporary directory
                if "temp_dir" in pending_assets and os.path.exists(pending_assets["temp_dir"]):
                    shutil.rmtree(pending_assets["temp_dir"], ignore_errors=True)
        
        # Also check for pending assets stored in file (backup method)
        assets_info_path = os.path.join(project_folder_path, ".launcher", "pending_assets.json")
        if os.path.exists(assets_info_path):
            try:
                with open(assets_info_path, "r") as f:
                    assets_info = json.load(f)
                
                new_paths = copy_workflow_assets(assets_info["assets"], project_folder_path)
                
                # Clean up
                os.remove(assets_info_path)
                if "temp_dir" in assets_info and os.path.exists(assets_info["temp_dir"]):
                    shutil.rmtree(assets_info["temp_dir"], ignore_errors=True)
                    
            except Exception as e:
                log('warning', f'Failed to process pending assets file: {str(e)}')
        
        # Validate installation
        # Auto-download missing models BEFORE validation
        if launcher_json and launcher_json.get("workflow_json"):
            set_launcher_state_data(
                project_folder_path,
                {
                    "status_message": "Checking for missing models...",
                    "state": "downloading_models",
                },
            )
            progress({'stage': 'downloading_models', 'progress': 0})
            log('info', 'Checking for missing models to auto-download')
            
            download_result = auto_download_models(
                project_folder_path,
                launcher_json["workflow_json"],
                log_callback=log
            )
            
            if download_result["downloaded"] > 0:
                log('info', f'Successfully auto-downloaded {download_result["downloaded"]} models')
            if download_result["failed"] > 0:
                log('warning', f'Failed to auto-download {download_result["failed"]} models: {download_result["failed_models"]}')
            
            progress({'stage': 'downloading_models', 'progress': 100})
        
        set_launcher_state_data(
            project_folder_path,
            {
                "status_message": "Validating installation...",
                "state": "validating",
            },
        )
        progress({'stage': 'validating', 'progress': 0})
        log('info', 'Validating installation')
        
        validator = InstallationValidator(project_folder_path)
        validation_results = validator.validate_all(launcher_json)
        validator.print_validation_report()
        
        progress({'stage': 'validating', 'progress': 100})
        log('info', 'Validation complete', validation_results['summary'])
        
        # Store validation results
        set_launcher_state_data(
            project_folder_path,
            {
                "validation_results": validation_results
            },
        )
        
        # Set final status based on validation
        if validation_results["summary"]["all_valid"]:
            set_launcher_state_data(
                project_folder_path, {"status_message": "Ready", "state": "ready"}
            )
            log('info', 'Project installation completed successfully')
            progress({'stage': 'complete', 'progress': 100})
        else:
            issue_count = sum(len(v['invalid']) for v in validation_results.values() if isinstance(v, dict) and 'invalid' in v)
            set_launcher_state_data(
                project_folder_path, 
                {
                    "status_message": f"Ready (with {issue_count} issues)",
                    "state": "ready_with_issues"
                }
            )
            log('warning', f'Project installation completed with {issue_count} issues')
            progress({'stage': 'complete', 'progress': 100, 'has_issues': True})
    except Exception as e:
        log('error', f'Project creation failed: {str(e)}')
        progress({'stage': 'error', 'error': str(e)})
        # remove the project folder if an error occurs
        shutil.rmtree(project_folder_path, ignore_errors=True)
        raise