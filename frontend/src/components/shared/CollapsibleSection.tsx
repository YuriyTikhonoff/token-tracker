import { useState, type ReactNode } from "react";

interface CollapsibleSectionProps {
  title: string;
  subtitle?: ReactNode;
  defaultExpanded?: boolean;
  children: ReactNode;
}

export function CollapsibleSection({
  title,
  subtitle,
  defaultExpanded = false,
  children,
}: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <section className="mb-8">
      <h2
        className="flex cursor-pointer items-center gap-2 border-b border-[#262b36] pb-[0.4rem] text-[1rem] text-[#c7cbd4] select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span
          className={`inline-block text-[0.7rem] text-[#8a8f98] transition-transform duration-150 ease-in-out ${isExpanded ? "rotate-90" : ""}`}
        >
          ▶
        </span>
        {title} {subtitle}
      </h2>
      {isExpanded && children}
    </section>
  );
}
