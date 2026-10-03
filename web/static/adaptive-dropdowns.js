// Keep custom menus attached to their controls; native selects keep the OS picker.
const root = document.documentElement;
const selector = '#rc-perfil-dropdown, .ttra-site-menu, .dropdown-color-lista, #sugerencias-direccion, #perfil-sugerencias-direccion';
const active = new Map();
let frame = 0;
function triggerFor(menu) {
  if (menu.id === 'rc-perfil-dropdown') return document.getElementById('btn-perfil-toggle');
  if (menu.matches('.ttra-site-menu')) return menu.parentElement.querySelector('.ttra-site-profile');
  if (menu.matches('.dropdown-color-lista')) return menu.parentElement.querySelector('.dropdown-color-boton');
  return document.getElementById(menu.id === 'sugerencias-direccion' ? 'direccion-entrega' : 'domicilio-direccion');
}
function position(menu, trigger) {
  const v = window.visualViewport;
  const left = (v?.offsetLeft || 0)+12, top = (v?.offsetTop || 0)+12;
  const right = left+(v?.width || innerWidth)-24, bottom = top+(v?.height || innerHeight)-24;
  const r = trigger.getBoundingClientRect();
  const profile = menu.matches('#rc-perfil-dropdown, .ttra-site-menu');
  // Mobile selectors follow their control's width instead of a 200px floor.
  // Account icon menus contain navigation labels and retain room for readable text.
  const mobileSelector = matchMedia('(max-width: 700px)').matches && !profile;
  const width = Math.min(right-left, mobileSelector ? r.width : Math.max(profile ? 240 : 200, r.width));
  Object.assign(menu.style,{position:'fixed',inset:'auto',margin:'0',width:`${width}px`,minWidth:'0',maxWidth:`${right-left}px`});
  // Popovers escape clipped cards and transformed section ancestors without
  // reparenting the menu, so its existing event handlers still work.
  if (typeof menu.showPopover === 'function' && !menu.matches(':popover-open')) menu.showPopover();
  const wanted = Math.min(menu.scrollHeight, 360);
  const below = Math.max(0,bottom-r.bottom-8), above = Math.max(0,r.top-top-8);
  const up = below<wanted && above>below;
  const height = Math.min(wanted,up?above:below);
  const x = Math.max(left,Math.min(profile?r.right-width:r.left,right-width));
  const y = Math.max(top,Math.min(bottom-height,up?r.top-8-height:r.bottom+8));
  menu.dataset.placement = up?'top':'bottom';
  menu.style.maxHeight=`${Math.max(0,height)}px`;
  menu.style.left=`${x}px`;menu.style.top=`${y}px`;
  if(typeof menu.showPopover !== 'function') {
    menu.style.position='absolute';
    const parent=menu.offsetParent;
    const bounds=parent?.getBoundingClientRect() || {left:0,top:0,width:innerWidth};
    const scale=parent?.offsetWidth ? bounds.width/parent.offsetWidth : 1;
    menu.style.left=`${(x-bounds.left)/scale+(parent?.scrollLeft||0)}px`;
    menu.style.top=`${(y-bounds.top)/scale+(parent?.scrollTop||0)}px`;
  }
}
function sync() {
  frame=0;
  if(root.dataset.modo!=='classic') return;
  for(const menu of document.querySelectorAll(selector)) {
    const trigger=triggerFor(menu);
    const open=trigger && !menu.hidden && !menu.classList.contains('oculto') && trigger.getClientRects().length;
    if(!open) {
      if(typeof menu.hidePopover==='function' && menu.matches(':popover-open'))menu.hidePopover();
      active.delete(menu);continue;
    }
    if(!menu.dataset.ttraMenu) {
      menu.dataset.ttraMenu='true';
      if(typeof menu.showPopover==='function')menu.setAttribute('popover','manual');
    }
    active.set(menu,trigger);
    position(menu,trigger);
  }
  for(const menu of active.keys())if(!menu.isConnected)active.delete(menu);
}
function schedule(){if(!frame)frame=requestAnimationFrame(sync);}
// r.target.closest(selector) importa tanto como r.target.matches(selector):
// un ítem ADENTRO de un menú abierto (ej. "Pedidos"/"Cerrar sesión" en
// #rc-perfil-dropdown) puede cambiar de oculto a visible después de que el
// menú ya midió su maxHeight una vez (la sesión se confirma async) — sin
// esto, ese cambio no dispara un recálculo y el menú queda con una altura
// vieja que recorta los ítems agregados después de la primera medición.
new MutationObserver(records=>{
  if(records.some(r=>r.type==='childList' ? [...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&(n.matches(selector)||n.querySelector(selector))) : r.target.matches(selector)||r.target===root||r.target===document.body||r.target.closest?.(selector)))schedule();
}).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden']});
window.addEventListener('resize',schedule,{passive:true});
window.addEventListener('scroll',event=>{
  if(![...active.keys()].some(menu=>menu.contains(event.target)))schedule();
},{capture:true,passive:true});
window.visualViewport?.addEventListener('resize',schedule,{passive:true});
window.visualViewport?.addEventListener('scroll',schedule,{passive:true});
document.addEventListener('keydown',event=>{
  if(event.key!=='Escape')return;
  for(const [menu,trigger] of active) {
    if(menu.hidden || menu.classList.contains('oculto')) continue;
    if(menu.matches('#rc-perfil-dropdown, .ttra-site-menu, .dropdown-color-lista'))trigger.click();
    else {menu.hidden=true;menu.classList.add('oculto');}
    trigger.focus({preventScroll:true});
  }
  schedule();
});
schedule();
