import * as React from "react";
import { cn } from "../../lib/utils";

const Progress = React.forwardRef(({ className, value, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "relative h-4 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800",
        className
      )}
      {...props}
    >
      <div
        className="h-full w-full flex-1 bg-gray-900 transition-all dark:bg-gray-400"
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </div>
  );
});
Progress.displayName = "Progress";

export { Progress };
