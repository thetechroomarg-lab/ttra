import { createRoot, type Root } from "react-dom/client"
import { MagneticDock, type DockItemData } from "@/components/ui/magnetic-dock"
import "./dock.css"

// Íconos de trazo (24x24) en el mismo estilo que los del dock.
const svg = (children: React.ReactNode) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-full h-full">
    {children}
  </svg>
)

const ICONOS: Record<string, React.ReactNode> = {
  Celulares: svg(<><rect x="7" y="2" width="10" height="20" rx="2" /><line x1="11" y1="18" x2="13" y2="18" /></>),
  Tablets: svg(<><rect x="4" y="3" width="16" height="18" rx="2" /><line x1="11" y1="18" x2="13" y2="18" /></>),
  "Notebooks y Macbooks": svg(<><rect x="4" y="5" width="16" height="11" rx="1.5" /><path d="M2 20h20" /></>),
  Gaming: svg(<><path d="M6 11h4M8 9v4" /><line x1="15" y1="12" x2="15.01" y2="12" /><line x1="18" y1="10" x2="18.01" y2="10" /><path d="M17.3 5H6.7a4 4 0 0 0-3.9 3.1l-1.5 6.5A3 3 0 0 0 4.2 18c.8 0 1.5-.4 2-1l1.3-1.5h9l1.3 1.5c.5.6 1.2 1 2 1a3 3 0 0 0 2.9-3.4l-1.5-6.5A4 4 0 0 0 17.3 5z" /></>),
  "Accesorios Celulares": svg(<><path d="M3 15v-3a9 9 0 0 1 18 0v3" /><rect x="3" y="14" width="4" height="6" rx="1.5" /><rect x="17" y="14" width="4" height="6" rx="1.5" /></>),
  BusquedaMarca: svg(<><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z" /><circle cx="7.5" cy="7.5" r="1.2" /></>),
}

export interface CategoriaDock {
  clave: string
  etiqueta: string
}

const raices = new WeakMap<Element, Root>()

function montar(el: HTMLElement, categorias: CategoriaDock[], alElegir: (clave: string) => void) {
  const items: DockItemData[] = categorias.map((c) => ({
    id: c.clave,
    label: c.etiqueta,
    icon: ICONOS[c.clave] ?? ICONOS.BusquedaMarca,
    onClick: () => alElegir(c.clave),
  }))
  let raiz = raices.get(el)
  if (!raiz) {
    raiz = createRoot(el)
    raices.set(el, raiz)
  }
  raiz.render(<MagneticDock items={items} iconSize={56} />)
}

;(window as unknown as { TTRADock: unknown }).TTRADock = { montar }
