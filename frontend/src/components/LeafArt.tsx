// Decorative leaf drawing used on the login page and dashboard banner.
export function LeafArt({ className }: { className?: string }) {
  return (
    <svg className={className} style={{ color: '#ffffff' }} viewBox="0 0 200 200" fill="none" aria-hidden="true">
      <path d="M100 190C46 160 30 92 100 10c70 82 54 150 0 180Z" fill="currentColor" />
      <path d="M100 190V40" stroke="#000" strokeOpacity=".35" strokeWidth="3" />
      {[60, 85, 110, 135, 160].map((y) => (
        <g key={y} stroke="#000" strokeOpacity=".3" strokeWidth="2.5" strokeLinecap="round">
          <path d={`M100 ${y}c-14-8-24-18-30-30`} />
          <path d={`M100 ${y}c14-8 24-18 30-30`} />
        </g>
      ))}
    </svg>
  );
}
