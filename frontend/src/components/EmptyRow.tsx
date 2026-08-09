interface EmptyRowProps {
  colSpan: number;
  label: string;
}

export function EmptyRow({ colSpan, label }: EmptyRowProps) {
  return (
    <tr>
      <td colSpan={colSpan} className="p-2 text-[#8a8f98] italic">
        {label}
      </td>
    </tr>
  );
}
