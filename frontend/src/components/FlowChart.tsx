import { useEffect, useRef } from 'react'
import { BarController, BarElement, CategoryScale, Chart, Legend, LinearScale, Tooltip } from 'chart.js'
import type { Flow } from '../types'
import { quantity } from '../format'

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend)

export default function FlowChart({ flow, unit }: { flow: Flow; unit: string }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const rows = flow.items.filter(row => row.unit === unit)
  const dates: string[] = []
  const cursor = new Date(`${flow.date_from}T00:00:00Z`)
  const end = new Date(`${flow.date_to}T00:00:00Z`)
  while (cursor <= end) { dates.push(cursor.toISOString().slice(0, 10)); cursor.setUTCDate(cursor.getUTCDate() + 1) }
  const values = new Map(rows.map(row => [row.date, row]))
  useEffect(() => {
    if (!canvas.current) return
    const chart = new Chart(canvas.current, {
      type: 'bar',
      data: {
        labels: dates.map(date => date.slice(5).split('-').reverse().join('/')),
        datasets: [
          { label: `Nhập (${unit})`, data: dates.map(date => Number(values.get(date)?.inbound ?? 0)), backgroundColor: '#185d49', borderRadius: 3, maxBarThickness: 19 },
          { label: `Xuất (${unit})`, data: dates.map(date => Number(values.get(date)?.outbound ?? 0)), backgroundColor: '#bac8bb', borderRadius: 3, maxBarThickness: 19 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 200 },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: item => `${item.dataset.label}: ${quantity(item.parsed.y ?? 0)}` } } },
        scales: { x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 8, color: '#6b746e', font: { size: 11, family: 'Be Vietnam Pro' } } }, y: { beginAtZero: true, border: { display: false }, grid: { color: '#edf0e9' }, ticks: { color: '#6b746e', precision: unit === 'PCS' ? 0 : 3, font: { size: 11 } } } },
      },
    })
    return () => chart.destroy()
  }, [flow, unit])
  return <><div className="chart-canvas"><canvas ref={canvas} role="img" aria-label={`Biểu đồ nhập và xuất ${unit}, từ ${flow.date_from} đến ${flow.date_to}`} /></div><details className="chart-data"><summary>Xem dữ liệu biểu đồ</summary><div className="table-scroll"><table><thead><tr><th>Ngày</th><th>Nhập ({unit})</th><th>Xuất ({unit})</th></tr></thead><tbody>{rows.map(row => <tr key={row.date}><td>{row.date}</td><td>{quantity(row.inbound)}</td><td>{quantity(row.outbound)}</td></tr>)}</tbody></table></div></details></>
}
