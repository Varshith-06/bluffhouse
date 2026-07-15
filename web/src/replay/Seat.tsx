import type { GameEvent } from "../types";
import type { TableState } from "../lib/reduce";
import { playerColor } from "../lib/format";
import type { Pov } from "./ReplayApp";
import type { SeatGeom } from "./geometry";
import { CardFace } from "./CardFace";
import { AnimatedNumber } from "./AnimatedNumber";

function chipCountFor(amount: number, bb: number): { count: number; tone: string } {
  const count = amount <= bb ? 1 : amount <= 4 * bb ? 2 : amount <= 12 * bb ? 3 : 4;
  const tone = amount <= 2 * bb ? "" : amount <= 10 * bb ? " blue" : " dark";
  return { count, tone };
}

export function Seat({
  id,
  geom,
  state,
  event,
  agentIds,
  pov,
  heat,
  showHeat,
  isButton,
  bigBlind,
  faded = false,
}: {
  id: string;
  geom: SeatGeom;
  state: TableState;
  event: GameEvent | undefined;
  agentIds: string[];
  pov: Pov;
  heat?: { suspicion: number; delta: number };
  showHeat: boolean;
  isButton: boolean;
  bigBlind: number;
  faded?: boolean;
}) {
  const folded = Boolean(state.folded[id]);
  const allin = Boolean(state.allin[id]) && !folded;
  const color = playerColor(agentIds, id);

  const involved =
    event &&
    (("agent_id" in event && event.agent_id === id) ||
      ("sender" in event && event.sender === id));
  const winner = involved && event?.type === "pot_awarded";
  const actor = involved && !winner;

  const canSee = pov === "truth" || pov === id;
  const shown = state.revealed[id] ?? (canSee ? state.hole[id] : null);
  const hasCards = Boolean(state.hole[id]) && !folded;

  const bet = state.bets[id] ?? 0;
  const suspicion = heat?.suspicion ?? 0;

  return (
    <>
      <div
        className={`seat${folded ? " folded" : ""}${actor ? " actor" : ""}${winner ? " winner" : ""}${faded ? " faded" : ""}`}
        style={{ left: `${geom.pct.x}%`, top: `${geom.pct.y}%` }}
      >
        <div className="hole">
          {hasCards &&
            (shown ? (
              shown.map((c, i) => <CardFace key={i} code={c} />)
            ) : (
              <>
                <CardFace back />
                <CardFace back />
              </>
            ))}
          {allin && <div className="allin-stamp">ALL IN</div>}
        </div>
        <div className="plaque" style={{ ["--accent" as string]: color }}>
          {suspicion > 0.12 && (
            <div
              className="heat-aura"
              style={{ opacity: Math.min(suspicion, 1) * 0.85 }}
            />
          )}
          <span className="ava" style={{ background: color }}>
            {id[0] ?? "?"}
          </span>
          <div className="pinfo">
            <div className="who">
              {id}
              {folded && <span className="tag quiet">Folded</span>}
            </div>
            <div className="stack mono">
              <AnimatedNumber value={state.stacks[id] ?? 0} />
            </div>
            {showHeat && (
              <div className="heat" title={`suspicion ${suspicion.toFixed(2)}`}>
                <div
                  className="heat-fill"
                  style={{ width: `${Math.min(suspicion, 1) * 100}%` }}
                />
              </div>
            )}
          </div>
          {isButton && <div className="dealer">D</div>}
        </div>
      </div>

      {bet > 0 && (
        <div
          className="wager"
          key={bet}
          style={
            {
              left: `${geom.wagerPct.x}%`,
              top: `${geom.wagerPct.y}%`,
              "--from-x": `${geom.pct.x}%`,
              "--from-y": `${geom.pct.y}%`,
            } as React.CSSProperties
          }
        >
          <div className="chip-stack">
            {Array.from({ length: chipCountFor(bet, bigBlind).count }, (_, i) => (
              <div key={i} className={`chip${chipCountFor(bet, bigBlind).tone}`} />
            ))}
          </div>
          <span className="wager-amt mono">{bet}</span>
        </div>
      )}
    </>
  );
}
