# Create new React project
npx create-next-app@latest counseling-frontend --typescript --tailwind --eslint

cd counseling-frontend

# Install dependencies
npm install @radix-ui/react-alert-dialog class-variance-authority clsx lucide-react tailwind-merge tailwindcss-animate

# Install shadcn/ui components
npx shadcn-ui@latest init

# Add required components
npx shadcn-ui@latest add card button alert

# Start development server
npm run dev