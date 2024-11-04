import * as React from "react"
import { Alert as AlertRoot } from "@radix-ui/react-alert"

const Alert = React.forwardRef(({ className, variant = "default", ...props }, ref) => (
  <AlertRoot ref={ref} className={`relative w-full rounded-lg border p-4 [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground [&:has(svg)]:pl-11 ${className}`} {...props} />
))
Alert.displayName = "Alert"

const AlertDescription = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={`text-sm [&_p]:leading-relaxed ${className}`} {...props} />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertDescription }
