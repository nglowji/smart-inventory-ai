from pathlib import Path

path = Path(__file__).resolve().parents[1] / "frontend/src/features/dashboard/FlowChart.tsx"
text = path.read_text(encoding="utf-8")
text = text.replace('import { useEffect,useRef }', 'import { useEffect,useMemo,useRef }')
text = 'import { chartData } from "./chartData";\n' + text
start = text.index('  const rows = flow.items.filter')
end = text.index('  useEffect(() =>', start)
text = text[:start] + '  const series = useMemo(() => chartData(flow, unit), [flow, unit]);\n' + text[end:]
start = text.index('        labels: dates.map(')
end = text.index('        datasets:', start)
text = text[:start] + '        labels: series.labels,\n' + text[end:]
text = text.replace('data: dates.map((date) => Number(values.get(date)?.inbound ?? 0)),', 'data: series.inbound,')
text = text.replace('data: dates.map((date) => Number(values.get(date)?.outbound ?? 0)),', 'data: series.outbound,')
text = text.replace('}, [flow, unit]);', '}, [series, unit]);').replace('{rows.map(', '{series.rows.map(')
path.write_text(text, encoding="utf-8")
