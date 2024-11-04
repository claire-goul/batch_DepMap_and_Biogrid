import * as React from "react"

const Button = React.forwardRef(({ className, variant = "default", size = "default", ...props }, ref) => {
  return (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ${
        variant === "outline" ? "border border-input bg-background hover:bg-accent hover:text-accent-foreground" : ""
      } ${
        size === "sm" ? "h-9 rounded-md px-3" : "h-10 px-4 py-2"
      } ${className}`}
      {...props}
    />
  )
})
Button.displayName = "Button"

export { Button }
