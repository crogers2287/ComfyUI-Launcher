'use client'

import { useMutation } from '@tanstack/react-query'
import React, { useEffect } from 'react'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { toast } from 'sonner'
import { Button } from './ui/button'
import { Config } from '@/lib/types'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { KeyIcon, ExternalLinkIcon } from 'lucide-react'
import { KeyboardShortcuts } from './KeyboardShortcuts'

function SettingsUI() {
    const [civitaiApiKey, setCivitaiApiKey] = React.useState<string>()

    const getSettingsQuery = useQuery({
        queryKey: ['settings'],
        queryFn: async () => {
            const resp = await fetch('/api/get_config')
            const data = (await resp.json()) as Config
            return data
        },
        enabled: !civitaiApiKey,
    })

    useEffect(() => {
        if (getSettingsQuery.data) {
            setCivitaiApiKey(getSettingsQuery.data.credentials.civitai.apikey)
        }
    }, [getSettingsQuery.data])


    const setCivitaiCredentialsMutation = useMutation({
        mutationFn: async ({
            civitai_api_key,
        }: {
            civitai_api_key: string
        }) => {
            const response = await fetch(`/api/update_config`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    credentials: {
                        civitai: {
                            apikey: civitai_api_key,
                        },
                    },
                }),
            })
            const data = await response.json()
            return data
        },
        onSuccess: async () => {
            toast.success('Saved your settings!')
        },
    })

    if (getSettingsQuery.isLoading) {
        return <div>Loading...</div>
    }

    return (
        <div className="flex flex-col p-6 max-w-6xl mx-auto">
            <div className="grid gap-6 md:grid-cols-2">
                {/* API Settings Card */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <KeyIcon className="h-5 w-5 text-primary" />
                            <CardTitle>API Configuration</CardTitle>
                        </div>
                        <CardDescription>
                            Configure external service API keys
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="civitai-key" className="text-sm font-medium">
                                CivitAI API Key
                            </Label>
                            <Input
                                id="civitai-key"
                                type="password"
                                placeholder="Your CivitAI API key"
                                className="font-mono"
                                value={civitaiApiKey}
                                onChange={(e) => setCivitaiApiKey(e.target.value)}
                            />
                            <div className="text-xs text-muted-foreground space-y-2">
                                <p>
                                    Get your API key from your{' '}
                                    <a
                                        href="https://civitai.com/user/account"
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-primary hover:underline inline-flex items-center gap-1"
                                    >
                                        CivitAI account settings
                                        <ExternalLinkIcon className="h-3 w-3" />
                                    </a>
                                </p>
                                <p className="text-xs">
                                    This key is stored locally and only used to download models from CivitAI.
                                </p>
                            </div>
                        </div>
                        <Button
                            onClick={(e) => {
                                e.preventDefault()
                                setCivitaiCredentialsMutation.mutate({
                                    civitai_api_key: civitaiApiKey || '',
                                })
                            }}
                            disabled={setCivitaiCredentialsMutation.isPending}
                            className="w-full"
                        >
                            {setCivitaiCredentialsMutation.isPending
                                ? 'Saving...'
                                : 'Save API Settings'}
                        </Button>
                    </CardContent>
                </Card>

                {/* Keyboard Shortcuts Card */}
                <KeyboardShortcuts />
            </div>
        </div>
    )
}

export default SettingsUI
