/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useEffect, useState } from "react";
import { api, nt, type EventInfo, type MerchantInfo } from "./types";

export default function OpsTab({ merchants, events }: { merchants: MerchantInfo[]; events: EventInfo[] }) {
  const [merchant, setMerchant] = useState(merchants[0]?.id);
  const [event, setEvent] = useState(events[0]?.id);
  const [elapsed, setElapsed] = useState(0.5);
  const [csv, setCsv] = useState("");
  const [restock, setRestock] = useState<any>(null);
  const [cal, setCal] = useState<any>(null);
  const [multi, setMulti] = useState<any>(null);

  useEffect(() => {
    api("/api/restock/multiday", { event_id: "evt_lunar_market", merchant_id: "merchant_newyear_01" }).then(setMulti);
  }, []);

  const sales = () => Object.fromEntries(csv.split("\n").map((l) => l.split(","))
    .filter((r) => r.length >= 2 && /^\d+$/.test(r[1].trim())).map((r) => [r[0].trim(), +r[1]]));
  const body = () => ({ event_id: event, merchant_id: merchant, elapsed, sales: sales() });
  const simulate = async () => {
    const r = await api<{ sales: Record<string, number> }>("/api/sales/simulate", { event_id: event, merchant_id: merchant, elapsed });
    setCsv("sku_id,units_sold\n" + Object.entries(r.sales).map(([k, v]) => `${k},${v}`).join("\n"));
    setRestock(null); setCal(null);
  };
  const sel = "rounded-md border border-stone-300 bg-white px-2 py-1";
  const btn = "rounded-md border border-stone-300 bg-white px-3 py-1.5";

  return (
    <div className="mt-6 space-y-5 text-sm">
      <p className="rounded-md bg-amber-50 px-3 py-2 text-amber-900">
        Simulation: no POS or supplier system is connected. Sales are pasted by hand or generated; treat every number here as illustrative.
      </p>
      <section className="rounded-xl border border-stone-200 bg-white p-5">
        <h2 className="font-semibold">Mid-event restock from sales</h2>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select className={sel} value={merchant} onChange={(e) => setMerchant(e.target.value)}>
            {merchants.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
          <select className={sel} value={event} onChange={(e) => setEvent(e.target.value)}>
            {events.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
          <label className="flex items-center gap-2">Event elapsed {Math.round(elapsed * 100)}%
            <input type="range" min={0.1} max={0.9} step={0.1} value={elapsed} onChange={(e) => setElapsed(+e.target.value)} /></label>
        </div>
        <div className="mt-3 grid gap-4 lg:grid-cols-3">
          <div>
            <textarea value={csv} onChange={(e) => setCsv(e.target.value)} rows={10} placeholder={"sku_id,units_sold\nSKU01,12"}
              className="w-full rounded-md border border-stone-300 p-2 font-mono text-xs" />
            <div className="mt-2 flex flex-wrap gap-2">
              <button className={btn} onClick={simulate}>Simulate sales</button>
              <button className="rounded-md bg-stone-900 px-3 py-1.5 text-white" onClick={() => api("/api/sales/restock", body()).then(setRestock)}>Recommend restock</button>
              <button className={btn} onClick={() => api("/api/calibration", body()).then(setCal)}>Calibrate</button>
            </div>
          </div>
          <div className="lg:col-span-2">
            {restock && (<>
              <p>Restock <b>{nt(restock.restock_cost)}</b> of {nt(restock.restock_budget)} available. <span className="text-stone-500">{restock.note}</span></p>
              <table className="mt-2 w-full"><thead className="text-left text-xs text-stone-500"><tr>
                <th className="pb-1 font-medium">SKU</th><th className="pb-1 text-right font-medium">Sold / stocked</th>
                <th className="pb-1 text-right font-medium">Forecast → updated</th><th className="pb-1 text-right font-medium">Restock</th>
                <th className="pb-1 pl-3 font-medium">Basis</th></tr></thead>
                <tbody>{restock.skus.filter((s: any) => s.stocked || s.restock_qty).map((s: any) => (
                  <tr key={s.sku_id} className="border-t border-stone-100">
                    <td className="py-1">{s.name}</td>
                    <td className="text-right tabular-nums">{s.sold} / {s.stocked}{s.sold_out && <span className="ml-1 text-xs text-rose-600">sold out</span>}</td>
                    <td className="text-right tabular-nums">{s.forecast_total} → {s.updated_total}</td>
                    <td className="text-right font-semibold tabular-nums">{s.restock_qty ? "+" + s.restock_qty : "–"}</td>
                    <td className="pl-3 text-xs text-stone-500">{s.basis}</td></tr>))}</tbody></table>
            </>)}
            {cal && (
              <div className="mt-4 rounded-md bg-stone-50 p-3">
                <b>Calibration for the next event</b>
                <span className="ml-2 text-stone-500">forecast error on items that did not sell out: {cal.mape_uncensored == null ? "–" : Math.round(cal.mape_uncensored * 100) + "%"}</span>
                <div className="mt-1 flex flex-wrap gap-1.5">{cal.skus.map((s: any) => (
                  <span key={s.sku_id} className="rounded bg-white px-2 py-0.5 text-xs">{s.name} ×{s.weight}</span>))}</div>
                <p className="mt-1 text-xs text-stone-500">{cal.note}</p>
              </div>
            )}
            {!restock && !cal && <p className="text-stone-400">Paste sales as CSV or simulate them, then ask for a restock.</p>}
          </div>
        </div>
      </section>

      {multi && (
        <section className="rounded-xl border border-stone-200 bg-white p-5">
          <h2 className="font-semibold">Multi-day restock · Lunar New Year Market ({multi.days} days)</h2>
          <p className="mt-1 text-stone-600">Day 1 is a firm order ({nt(multi.day1_cost)} of {nt(multi.budget)}). Later days are expected orders that move with actual sales. Expected profit {nt(multi.expected_profit)}.</p>
          <table className="mt-3 w-full"><thead className="text-left text-xs text-stone-500"><tr>
            <th className="pb-1 font-medium">SKU</th><th className="pb-1 font-medium">Shelf life</th>
            {multi.day_curve.map((_: number, d: number) => <th key={d} className="pb-1 text-right font-medium">Day {d + 1}</th>)}
            <th className="pb-1 text-right font-medium">Unsold / expired</th></tr></thead>
            <tbody>{multi.skus.map((s: any) => (
              <tr key={s.sku_id} className="border-t border-stone-100">
                <td className="py-1">{s.name}</td>
                <td>{s.shelf_life_days > 365 ? "long" : s.shelf_life_days + " d"}</td>
                {s.orders.map((o: any) => <td key={o.day} className={`text-right tabular-nums ${o.firm ? "font-semibold" : ""}`}>{Math.round(o.order_mean)}</td>)}
                <td className="text-right tabular-nums">{s.expected_unsold_or_expired}</td></tr>))}</tbody></table>
          <p className="mt-2 text-xs text-stone-400">{multi.note}</p>
        </section>
      )}
    </div>
  );
}
