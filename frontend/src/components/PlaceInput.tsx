/**
 * Text input with debounced geocoder suggestions for origin and destination entry.
 * Accepts free text as well, so an unmatched address still reaches the backend geocoder.
 */

import { useId, useRef, useState } from "react";

import type { Place } from "../api/types";
import { usePlaceSearch } from "../hooks/usePlanning";

interface PlaceInputProps {
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
  onSelect: (place: Place) => void;
}

export function PlaceInput({ label, value, placeholder, onChange, onSelect }: PlaceInputProps) {
  const inputId = useId();
  const [open, setOpen] = useState(false);
  const blurTimer = useRef<number | undefined>(undefined);
  const { data, isFetching } = usePlaceSearch(open ? value : "");
  const results = data?.results ?? [];

  const choose = (place: Place) => {
    onSelect(place);
    setOpen(false);
  };

  return (
    <div className="relative">
      <label htmlFor={inputId} className="mb-1 block text-xs font-medium text-slate-600">
        {label}
      </label>
      <input
        id={inputId}
        type="text"
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
        onChange={(event) => {
          onChange(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          blurTimer.current = window.setTimeout(() => setOpen(false), 150);
        }}
      />

      {open && value.trim().length >= 3 && (
        <ul className="absolute z-30 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
          {isFetching && results.length === 0 && (
            <li className="px-3 py-2 text-xs text-slate-500">Searching…</li>
          )}
          {!isFetching && results.length === 0 && (
            <li className="px-3 py-2 text-xs text-slate-500">No matches. Free text is accepted.</li>
          )}
          {results.map((place) => (
            <li key={`${place.lat},${place.lon},${place.label}`}>
              <button
                type="button"
                className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-sky-50"
                onMouseDown={(event) => {
                  event.preventDefault();
                  window.clearTimeout(blurTimer.current);
                  choose(place);
                }}
              >
                {place.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
