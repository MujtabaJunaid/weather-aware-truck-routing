/**
 * Trip entry form: origin, destination, departure, load weight and checkpoint interval.
 * Resolved geocoder coordinates are sent when the driver picked a suggestion, so the backend
 * does not have to guess at an address a second time.
 */

import { useState } from "react";

import type { Place, PlanRequest } from "../api/types";
import { fromLocalInputValue, pounds } from "../lib/format";
import { PlaceInput } from "./PlaceInput";

const INTERVALS = [10, 25, 50] as const;

interface TripFormProps {
  defaultDeparture: string;
  isPending: boolean;
  onSubmit: (payload: PlanRequest) => void;
}

export function TripForm({ defaultDeparture, isPending, onSubmit }: TripFormProps) {
  const [origin, setOrigin] = useState("Chicago, IL");
  const [originPlace, setOriginPlace] = useState<Place | null>(null);
  const [destination, setDestination] = useState("Denver, CO");
  const [destinationPlace, setDestinationPlace] = useState<Place | null>(null);
  const [departure, setDeparture] = useState(defaultDeparture);
  const [loadWeight, setLoadWeight] = useState(42_000);
  const [interval, setInterval] = useState<(typeof INTERVALS)[number]>(25);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();

    const payload: PlanRequest = {
      departure_time: fromLocalInputValue(departure),
      load_weight_lb: loadWeight,
      checkpoint_interval_miles: interval,
    };

    if (originPlace && originPlace.label === origin) {
      payload.origin = originPlace.label;
      payload.origin_lat = originPlace.lat;
      payload.origin_lon = originPlace.lon;
    } else {
      payload.origin = origin;
    }

    if (destinationPlace && destinationPlace.label === destination) {
      payload.destination = destinationPlace.label;
      payload.destination_lat = destinationPlace.lat;
      payload.destination_lon = destinationPlace.lon;
    } else {
      payload.destination = destination;
    }

    onSubmit(payload);
  };

  const disabled = isPending || origin.trim().length < 2 || destination.trim().length < 2;

  return (
    <form onSubmit={submit} className="space-y-4">
      <PlaceInput
        label="Origin"
        value={origin}
        placeholder="City, state or address"
        onChange={setOrigin}
        onSelect={(place) => {
          setOriginPlace(place);
          setOrigin(place.label);
        }}
      />

      <PlaceInput
        label="Destination"
        value={destination}
        placeholder="City, state or address"
        onChange={setDestination}
        onSelect={(place) => {
          setDestinationPlace(place);
          setDestination(place.label);
        }}
      />

      <div>
        <label htmlFor="departure" className="mb-1 block text-xs font-medium text-slate-600">
          Departure
        </label>
        <input
          id="departure"
          type="datetime-local"
          value={departure}
          onChange={(event) => setDeparture(event.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
        />
      </div>

      <div>
        <label htmlFor="weight" className="mb-1 flex items-baseline justify-between text-xs font-medium text-slate-600">
          <span>Load weight</span>
          <span className="font-semibold text-slate-900">{pounds(loadWeight)}</span>
        </label>
        <input
          id="weight"
          type="range"
          min={0}
          max={80_000}
          step={1_000}
          value={loadWeight}
          onChange={(event) => setLoadWeight(Number(event.target.value))}
          className="w-full accent-sky-600"
        />
        <div className="mt-1 flex justify-between text-[10px] text-slate-400">
          <span>empty</span>
          <span>30k</span>
          <span>40k</span>
          <span>80k</span>
        </div>
      </div>

      <fieldset>
        <legend className="mb-1 text-xs font-medium text-slate-600">Checkpoint interval</legend>
        <div className="grid grid-cols-3 gap-2">
          {INTERVALS.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setInterval(option)}
              className={`rounded-lg border px-2 py-2 text-sm font-medium transition ${
                interval === option
                  ? "border-sky-600 bg-sky-600 text-white shadow-sm"
                  : "border-slate-300 bg-white text-slate-700 hover:border-sky-400"
              }`}
            >
              {option} mi
            </button>
          ))}
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={disabled}
        className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        {isPending ? "Checking weather along each route…" : "Plan route"}
      </button>
    </form>
  );
}
