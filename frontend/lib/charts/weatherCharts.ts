// WISP 3: app/frontend/lib/charts/weatherCharts.ts (only tableTsv, which DataDialog uses; the weather panels are adapted in a later wave)

/** A table as tab-separated text for the clipboard (a spreadsheet pastes it into cells): ISO dates, as shown otherwise */
export function tableTsv(table: {
  columns: string[]
  rows: { date: string; forecast: boolean; values: (string | null)[] }[]
}) {
  const clean = (text: string) => text.replace(/[\t\r\n]+/g, ' ')
  return [
    ['Date', 'Forecast', ...table.columns],
    ...table.rows.map((row) => [row.date, row.forecast ? 'yes' : 'no', ...row.values.map((value) => value ?? '')]),
  ]
    .map((cells) => cells.map(clean).join('\t'))
    .join('\n')
}
