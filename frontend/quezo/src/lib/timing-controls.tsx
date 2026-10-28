"use client";

import { useEffect, useState } from "react";

export type TimingChoice = "standard" | "adjusted" | "off";

export function TimingControls({ authoredDuration, choice, onChoice, duration, onDuration, disabled = false }: {
  authoredDuration: number | null; choice: TimingChoice; onChoice: (choice: TimingChoice) => void;
  duration: number; onDuration: (duration: number) => void; disabled?: boolean;
}) {
  const [interactive, setInteractive] = useState(false);
  useEffect(() => setInteractive(true), []);
  return <fieldset disabled={disabled || !interactive}>
    <legend>Timing for this attempt</legend>
    <p>Choose before starting. This choice and the server deadline cannot change after start.
      Availability end always stops new starts, not an adjusted or timing-off attempt.</p>
    <label>Attempt timing<select value={choice}
      onChange={(event) => onChoice(event.target.value as TimingChoice)}>
      <option value="standard">Standard authored timing</option>
      <option value="adjusted">Adjusted duration</option>
      <option value="off">Timing off</option>
    </select></label>
    <p>Standard: {authoredDuration == null ? "no authored duration limit" :
      `${authoredDuration} seconds`}; any availability end also caps the deadline.
      Adjusted: chosen seconds from start, without the availability-end cap.
      Timing off: neither duration nor availability-end attempt deadline.</p>
    {choice === "adjusted" && <label>Adjusted duration (seconds)<input type="number" required
      min={60} max={6048000} step={1} value={duration}
      onChange={(event) => onDuration(Number(event.target.value))} /></label>}
  </fieldset>;
}

export function TimingPreview({ authoredDuration }: { authoredDuration: number | null }) {
  const [choice, setChoice] = useState<TimingChoice>("standard");
  const [duration, setDuration] = useState((authoredDuration ?? 60) * 10);
  return <section aria-label="Timing preview">
    <p>Preview only: try the pre-start timing controls. No deadline or attempt is created.</p>
    <TimingControls authoredDuration={authoredDuration} choice={choice} onChoice={setChoice}
      duration={duration} onDuration={setDuration} />
  </section>;
}
