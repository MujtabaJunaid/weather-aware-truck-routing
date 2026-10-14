/**
 * Display formatters for distances, durations, weights and forecast timestamps.
 * All times render in the viewer's local zone, which is what a driver reads off the clock.
 */

const TIME_FORMAT = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  hour: "numeric",
  minute: "2-digit",
});

const DATE_TIME_FORMAT = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function miles(value: number): string {
  return `${Math.round(value).toLocaleString()} mi`;
}

export function preciseMiles(value: number): string {
  return `${value.toFixed(1)} mi`;
}

export function duration(seconds: number): string {
  const total = Math.round(seconds / 60);
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  return hours > 0 ? `${hours} h ${minutes.toString().padStart(2, "0")} m` : `${minutes} m`;
}

export function clockTime(iso: string): string {
  return TIME_FORMAT.format(new Date(iso));
}

export function dateTime(iso: string): string {
  return DATE_TIME_FORMAT.format(new Date(iso));
}

export function pounds(value: number): string {
  return `${Math.round(value).toLocaleString()} lb`;
}

export function rate(value: number, unit: string): string {
  return `${value.toFixed(2)} ${unit}`;
}

export function toLocalInputValue(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function fromLocalInputValue(value: string): string {
  return new Date(value).toISOString();
}
