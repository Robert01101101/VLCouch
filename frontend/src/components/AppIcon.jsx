export default function AppIcon({ className = 'h-8 w-8' }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="6" fill="#141414" />
      <path d="M12 8.5v15l11-7.5-11-7.5z" fill="#e50914" />
    </svg>
  )
}
