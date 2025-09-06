import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'

const shortcuts = [
  { keys: ['Ctrl/Cmd', 'N'], action: 'Create new workflow' },
  { keys: ['Ctrl/Cmd', 'I'], action: 'Import workflow' },
  { keys: ['Ctrl/Cmd', 'S'], action: 'Open settings' },
  { keys: ['Ctrl/Cmd', '/'], action: 'Focus search' },
]

export function KeyboardShortcuts() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Keyboard Shortcuts</CardTitle>
        <CardDescription>
          Quick actions to navigate faster
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {shortcut.keys.map((key, keyIndex) => (
                  <Badge key={keyIndex} variant="secondary" className="font-mono text-xs">
                    {key}
                  </Badge>
                ))}
              </div>
              <span className="text-sm text-muted-foreground">
                {shortcut.action}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}