import { useMemo } from "react";

const MAX_CELLS = 480;

type Props = {
  /** One char per source block: 0 pending, 1 received directly, 2 recovered. */
  blocks: string;
};

type CellState = "pending" | "direct" | "repaired";

/**
 * Grid of source blocks. Blocks caught directly fill in solid; blocks whose
 * frames were missed light up in the accent color when repair frames recover
 * them — the fountain-code idea at a glance.
 */
export const BlockGrid = ({ blocks }: Props) => {
  const cells = useMemo<CellState[]>(() => {
    const k = blocks.length;
    const perCell = Math.max(1, Math.ceil(k / MAX_CELLS));
    const out: CellState[] = [];
    for (let i = 0; i < k; i += perCell) {
      const group = blocks.slice(i, i + perCell);
      out.push(
        group.includes("0")
          ? "pending"
          : group.includes("2")
            ? "repaired"
            : "direct",
      );
    }
    return out;
  }, [blocks]);

  const columns = Math.min(cells.length, cells.length > 120 ? 32 : 16);
  return (
    <div
      className="block-grid"
      style={{ gridTemplateColumns: `repeat(${Math.max(columns, 1)}, 1fr)` }}
      aria-hidden="true"
    >
      {cells.map((state, i) => (
        <span key={i} className={`block-cell is-${state}`} />
      ))}
    </div>
  );
};
