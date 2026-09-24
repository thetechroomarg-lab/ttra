import {fendiArtwork} from '/header-cat-art-fendi.js';

// Reuse Fendi's actual face (carey, ojos amarillos), con un cuerpo sentado
// de frente para su álbum -mismo patrón que vaiven.js/bitu.js-.
const mascot=document.getElementById('fendi-mascot');
const source=document.createElement('template');source.innerHTML=fendiArtwork;
const head=source.content.querySelector('.cat-head').cloneNode(true);
head.querySelectorAll('.cat-tongue,.cat-happy-eyes,.cat-strain-face,.cat-angry-face').forEach(el=>el.remove());
head.querySelector('.cat-mouth').setAttribute('d','M79 63V66M70 65Q79 77 88 65');
const pupils=head.querySelectorAll('.cat-eyes ellipse');
pupils[2].setAttribute('cx','65');pupils[3].setAttribute('cx','92');
mascot.innerHTML=`<svg viewBox="0 0 120 136" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <g fill="#3c2a1d" stroke="#22160e" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
    <path d="M38 117Q13 128 15 100" fill="none" stroke="#c99a68" stroke-width="10"/>
    <ellipse cx="60" cy="102" rx="28" ry="30"/>
    <ellipse cx="60" cy="99" rx="15" ry="23" fill="#3c2a1d" stroke="none"/>
    <ellipse cx="38" cy="120" rx="12" ry="9"/><ellipse cx="82" cy="120" rx="12" ry="9"/>
    <path d="M50 93L49 125Q53 131 58 125L57 94M64 94L63 125Q69 131 73 125L72 93"/>
    <path d="M51 125V129M55 126V130M67 126V130M71 125V129" stroke="#22160e" stroke-width="1"/>
    <g class="fendi-face" transform="translate(-18 -3)"></g>
    <path class="fendi-scratch-paw" d="M82 117Q101 103 91 73" fill="none" stroke="#3c2a1d" stroke-width="10"/>
  </g>
</svg>`;
mascot.querySelector('.fendi-face').append(head);

// Content remains visible if animation APIs are unavailable.
if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.documentElement.classList.add('fendi-ready');
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries)if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target);}
  },{threshold:.08});
  document.querySelectorAll('[data-fendi-reveal]').forEach(el=>observer.observe(el));
}

// This exception belongs only to the album's return button and is consumed once.
const returnHome=document.querySelector('.fendi-back');
let returnReady=false,returnPending=false;
returnHome?.addEventListener('click',async event=>{
  if(returnReady||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  event.preventDefault();event.stopImmediatePropagation();
  if(returnPending)return;
  returnPending=true;returnHome.setAttribute('aria-busy','true');
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),3000);
  let guest=true;
  try { const response=await fetch('/api/me',{cache:'no-store',signal:controller.signal});guest=!response.ok; }
  catch { /* Keep the return link usable even if session lookup is unavailable. */ }
  finally { clearTimeout(timeout); }
  try { sessionStorage.setItem('ttra_fendi_return_once',JSON.stringify({guest,at:Date.now()})); } catch {}
  returnReady=true;returnPending=false;returnHome.removeAttribute('aria-busy');returnHome.click();
});
