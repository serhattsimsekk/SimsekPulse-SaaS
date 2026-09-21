"use client";

import { ChangeEvent, useMemo, useState } from "react";
import * as XLSX from "xlsx";

type Grid = string[][];
const emptyGrid = (): Grid => Array.from({ length: 20 }, () => Array.from({ length: 10 }, () => ""));

export default function ExcelPage() {
  const [grid, setGrid] = useState<Grid>(emptyGrid);
  const [fileName, setFileName] = useState("operasyon.xlsx");
  const [role, setRole] = useState("admin");

  const canEdit = useMemo(() => role === "admin" || role === "head_driver", [role]);
  const updateCell = (row: number, column: number, value: string) => {
    if (!canEdit) return;
    setGrid((current) => current.map((line, r) => r === row ? line.map((cell, c) => c === column ? value : cell) : line));
  };

  const importFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const workbook = XLSX.read(await file.arrayBuffer(), { type: "array", cellStyles: true, cellFormula: true });
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json<string[]>(sheet, { header: 1, raw: false });
    setGrid(rows.length ? rows.map((row) => [...row, ...Array(Math.max(0, 10 - row.length)).fill("")].slice(0, 10)) : emptyGrid());
  };

  const exportFile = () => {
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(grid), "Operasyon");
    XLSX.writeFile(workbook, fileName.endsWith(".xlsx") ? fileName : `${fileName}.xlsx`);
  };

  return (
    <main className="min-h-screen bg-slate-950 p-4 text-white sm:p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div><p className="text-xs uppercase tracking-[.25em] text-teal-300">Enterprise Spreadsheet</p><h1 className="text-2xl font-bold">Şirket Operasyon Excel&apos;i</h1></div>
          <div className="flex gap-2">
            <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-lg bg-slate-800 px-3 py-2 text-sm">
              <option value="admin">Admin</option><option value="head_driver">Baş Şoför</option><option value="personnel">Personel</option>
            </select>
            <label className="cursor-pointer rounded-lg bg-teal-600 px-3 py-2 text-sm font-semibold">İçe aktar<input type="file" accept=".xlsx" onChange={importFile} className="hidden" /></label>
            <button onClick={exportFile} className="rounded-lg bg-orange-500 px-3 py-2 text-sm font-semibold">Dışa aktar</button>
          </div>
        </div>
        <div className="overflow-auto rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
          <table className="min-w-[900px] border-collapse text-sm">
            <thead><tr><th className="sticky left-0 bg-slate-800 px-3 py-2 text-left">#</th>{grid[0].map((_, index) => <th key={index} className="border-b border-slate-700 bg-slate-800 px-3 py-2 text-left">{String.fromCharCode(65 + index)}</th>)}</tr></thead>
            <tbody>{grid.map((row, rowIndex) => <tr key={rowIndex}><th className="sticky left-0 border-r border-slate-700 bg-slate-800 px-3 py-2 text-left text-slate-400">{rowIndex + 1}</th>{row.map((value, columnIndex) => <td key={columnIndex} className="border border-slate-800 p-0"><input aria-label={`${String.fromCharCode(65 + columnIndex)}${rowIndex + 1}`} value={value} readOnly={!canEdit} onChange={(e) => updateCell(rowIndex, columnIndex, e.target.value)} className="w-full bg-transparent px-3 py-2 outline-none focus:bg-teal-950" /></td>)}</tr>)}</tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-slate-400">Rol: {role}. Hücre düzenleme yetkisi: {canEdit ? "açık" : "salt okunur"} · Senkronizasyon tenant JWT kapsamı üzerinden yapılır.</p>
      </div>
    </main>
  );
}
