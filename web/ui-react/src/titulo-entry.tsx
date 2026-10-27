import { createRoot } from "react-dom/client"
import { TextRepel } from "@/components/ui/text-repel"
import "./titulo.css"

// Titulo de la entrada a /blackhole en la home: las letras se apartan del cursor.
const TEXTO = "¿¿¿ BLACK HOLE ???"

function montar() {
  const el = document.querySelector<HTMLElement>("[data-blackhole-titulo]")
  if (!el) return
  createRoot(el).render(<TextRepel text={TEXTO} className="justify-start cursor-pointer" radius={140} strength={50} />)
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", montar)
else montar()
