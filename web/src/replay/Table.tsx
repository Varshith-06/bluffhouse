import { useMemo } from "react";
import type { GameEvent, MessageSent, Reception, RunMeta } from "../types";
import type { TableState } from "../lib/reduce";
import { heatAt, potSize, streetOf } from "../lib/reduce";
import { MODALITY_META, playerColor } from "../lib/format";
import type { Pov } from "./ReplayApp";
import { seatGeometry } from "./geometry";
import { Seat } from "./Seat";
import { CardFace } from "./CardFace";
import { EffectsLayer } from "./EffectsLayer";
import { AnimatedNumber } from "./AnimatedNumber";

export function Table({
  run,
  events,
  allEvents,
  cursor,
  state,
  pov,
  hasLedgers,
  presenting,
  finale = false,
}: {
  run: RunMeta;
  events: GameEvent[];
  allEvents: GameEvent[];
  cursor: number;
  state: TableState;
  pov: Pov;
  hasLedgers: boolean;
  presenting: boolean;
  finale?: boolean;
}) {
  const event = events[cursor];
  const geoms = useMemo(() => seatGeometry(state.order), [state.order.join("|")]);
  const heat = useMemo(
    () => (hasLedgers && event ? heatAt(allEvents, event.seq) : {}),
    [hasLedgers, allEvents, event?.seq],
  );

  const pot = potSize(state);
  const street = streetOf(state);

  // spotlight: during a message, dim everyone who isn't part of the moment
  // (ground truth only — a POV must never reveal who else noticed)
  const spotlight = useMemo(() => {
    if (pov !== "truth" || event?.type !== "message_sent" || event.modality === "speech")
      return null;
    const inLight = new Set([event.sender, ...event.targets]);
    for (const [agent, r] of Object.entries(event.receptions ?? {})) {
      if (r.outcome !== "missed") inLight.add(agent);
    }
    return inLight;
  }, [pov, event]);

  return (
    <div className={`table-wrap${presenting ? " big" : ""}`}>
      <div className="felt">
        <div className="felt-inner" />

        <div className="table-center">
          <div className="street-label" key={`${event?.hand_no}-${street}`}>
            hand {event?.hand_no ?? ""} · {street}
          </div>
          <div className="board">
            {Array.from({ length: 5 }, (_, i) => (
              <CardFace key={i} code={state.board[i]} slot={!state.board[i]} big />
            ))}
          </div>
          <div className={`pot${pot > 0 ? "" : " empty"}`}>
            <span className="pot-chip" />
            <span className="mono">
              <AnimatedNumber value={pot} />
            </span>
          </div>
        </div>

        {state.order.map((id) => (
          <Seat
            key={id}
            id={id}
            geom={geoms[id]}
            state={state}
            event={event}
            agentIds={run.agent_ids}
            pov={pov}
            heat={heat[id]}
            showHeat={hasLedgers}
            isButton={state.button === id}
            bigBlind={run.big_blind}
            faded={Boolean(spotlight && !spotlight.has(id))}
          />
        ))}

        {event?.type === "message_sent" && (
          <MessageBubble e={event} pov={pov} geoms={geoms} agentIds={run.agent_ids} />
        )}

        <EffectsLayer event={event} state={state} geoms={geoms} pov={pov} agentIds={run.agent_ids} />

        {event?.type === "hand_started" && (
          <div className="hand-banner" key={event.event_id}>
            {event.hand_no === 1 && <span className="hand-banner-brand">bluffhouse</span>}
            <span className="hand-banner-no">HAND {event.hand_no}</span>
          </div>
        )}

        {finale && <Standings run={run} agentIds={run.agent_ids} />}
      </div>
    </div>
  );
}

function Standings({ run, agentIds }: { run: RunMeta; agentIds: string[] }) {
  const ranked = Object.entries(run.final_stacks).sort((a, b) => b[1] - a[1]);
  if (!ranked.length) return null;
  return (
    <div className="standings">
      <div className="standings-title">FINAL STANDINGS</div>
      {ranked.map(([id, stack], i) => (
        <div className={`standings-row${i === 0 ? " first" : ""}`} key={id} style={{ animationDelay: `${0.3 + i * 0.18}s` }}>
          <span className="standings-rank">{i === 0 ? "👑" : i + 1}</span>
          <span className="standings-name" style={{ color: playerColor(agentIds, id) }}>
            {id}
          </span>
          <span className="standings-stack mono">{stack}</span>
          <span className={`standings-delta mono ${stack >= run.starting_stack ? "up" : "down"}`}>
            {stack >= run.starting_stack ? "+" : ""}
            {stack - run.starting_stack}
          </span>
        </div>
      ))}
    </div>
  );
}

/** What the active POV perceives of a message: the bubble contents. */
function povReception(e: MessageSent, pov: Pov): Reception | null {
  if (pov === "truth") return { outcome: "clear", confidence: 1, text: null };
  return e.receptions?.[pov] ?? null;
}

function MessageBubble({
  e,
  pov,
  geoms,
  agentIds,
}: {
  e: MessageSent;
  pov: Pov;
  geoms: ReturnType<typeof seatGeometry>;
  agentIds: string[];
}) {
  const rec = povReception(e, pov);
  if (!rec || rec.outcome === "missed") return null;
  const geom = geoms[e.sender];
  if (!geom) return null;

  const meta = MODALITY_META[e.modality];
  const who = e.targets.join(", ");
  let from: string;
  let body: string | null = e.text;

  if (rec.outcome === "fragment") {
    from = e.modality === "note" ? `the note ${e.sender} passed, read` : `overheard from ${e.sender}`;
    body = rec.text;
  } else if (rec.outcome === "surface") {
    from = e.modality === "note" ? `${e.sender} slips something to ${who}` : `${e.sender} signals ${who}`;
    body = e.modality === "note" ? "(contents unseen)" : body;
  } else if (e.modality === "whisper") from = `${e.sender} whispers to ${who}`;
  else if (e.modality === "note") from = `${e.sender} slips a note to ${who}`;
  else if (e.modality === "accusation") from = `${e.sender} accuses ${who}`;
  else if (e.modality === "speech") from = `${e.sender} says`;
  else from = `${e.sender} signals ${who}`;

  return (
    <div
      className={`bubble m-${e.modality}${rec.outcome === "fragment" ? " fragment" : ""}`}
      style={{ left: `${geom.bubblePct.x}%`, top: `${geom.bubblePct.y}%` }}
    >
      <span className="bubble-from">
        <span className="bubble-icon">{meta.icon}</span>
        <span style={{ color: playerColor(agentIds, e.sender) }}>{from}</span>
        {rec.confidence < 1 && (
          <span className="bubble-conf mono">~{Math.round(rec.confidence * 100)}%</span>
        )}
      </span>
      {body}
    </div>
  );
}
