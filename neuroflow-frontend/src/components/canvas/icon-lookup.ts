import { Box, type LucideIcon } from 'lucide-react'
import * as icons from 'lucide-react'

// Descriptors carry kebab-case lucide names (docs/13-node-catalog-and-sdk.md
// #13.2, e.g. "mouse-pointer-click"); lucide-react exports PascalCase.
function toPascalCase(kebab: string): string {
  return kebab
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('')
}

export function iconForName(name: string): LucideIcon {
  const key = toPascalCase(name) as keyof typeof icons
  const icon = icons[key]
  return (icon as LucideIcon | undefined) ?? Box
}
