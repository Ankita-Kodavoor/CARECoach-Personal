import * as React from "react";
import { cn } from "../../lib/utils";

const Badge = React.forwardRef(({ className, variant = "default", ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-gray-950 focus:ring-offset-2 dark:border-gray-800 dark:focus:ring-gray-300",
        {
          "border-transparent bg-gray-900 text-gray-50 dark:bg-gray-50 dark:text-gray-900":
            variant === "default",
          "border-transparent bg-gray-900 text-gray-50 dark:bg-gray-50 dark:text-gray-900":
            variant === "primary",
          "border-transparent bg-red-500 text-gray-50 dark:bg-red-900 dark:text-gray-50":
            variant === "destructive",
          "border-transparent bg-green-500 text-gray-50 dark:bg-green-900 dark:text-gray-50":
            variant === "success",
          "border-transparent bg-yellow-500 text-gray-50 dark:bg-yellow-900 dark:text-gray-50":
            variant === "warning",
          "border-transparent bg-blue-500 text-gray-50 dark:bg-blue-900 dark:text-gray-50":
            variant === "info",
          "border-gray-200 bg-white text-gray-900 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-50":
            variant === "outline",
          "border-gray-200 bg-gray-100 text-gray-900 dark:border-gray-800 dark:bg-gray-800 dark:text-gray-50":
            variant === "secondary",
        },
        className
      )}
      {...props}
    />
  );
});
Badge.displayName = "Badge";

export { Badge };
