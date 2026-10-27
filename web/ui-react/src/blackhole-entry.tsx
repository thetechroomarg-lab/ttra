import { createRoot, type Root } from "react-dom/client"
import { Spiral3DSlider, type Spiral3DSlide } from "@/components/ui/spiral-3d-slider"
import DitherPrismHero from "@/components/ui/dither-prism-hero"
import "./blackhole.css"

const raices = new WeakMap<Element, Root>()

// Fondo de dither prismático en ámbar, detrás del spiral (mismos colores que el disco de acreción).
function montarFondo(el: HTMLElement) {
  createRoot(el).render(
    <DitherPrismHero
      className="absolute inset-0 h-full min-h-0 opacity-50"
      color1="#000000"
      color2="#6b2c04"
      color3="#ffc23a"
      speed={0.6}
      ditherIntensity={0.2}
      prismIntensity={0.05}
      particleCount={40}
      particleColor="#ffd27a"
    />,
  )
}

function montar(el: HTMLElement, items: Spiral3DSlide[], fondo?: HTMLElement | null) {
  if (fondo) montarFondo(fondo)
  let raiz = raices.get(el)
  if (!raiz) {
    raiz = createRoot(el)
    raices.set(el, raiz)
  }
  raiz.render(
    <Spiral3DSlider
      items={items}
      ariaLabel="Personas de todo el mundo"
      className="h-full min-h-0 bg-transparent dark:bg-transparent"
      autoSpeed={0.32}
      cardWidth={300}
      radius={260}
      verticalGap={70}
    />,
  )
}

;(window as unknown as { TTRABlackholeSlider: unknown }).TTRABlackholeSlider = { montar }
