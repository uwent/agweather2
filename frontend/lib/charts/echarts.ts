// WISP 3: app/frontend/lib/charts/echarts.ts (copied)
// ECharts, tree-shaken to the pieces WISP uses (and titles, for a model's stacked grids)
import { BarChart, LineChart } from 'echarts/charts'
import {
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  // A model's stacked grids name each grid with a title (modelCharts)
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
])

export { echarts }
export type { EChartsCoreOption } from 'echarts/core'

/** The days in view on a chart's date axis, as indexes */
export type ChartView = { start: number; end: number }
