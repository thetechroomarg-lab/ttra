/* Progressive 3D previews: keep the original artwork if WebGL is unavailable. */
(() => {
  const section=document.getElementById('ttra-explorar');
  if(!section)return;
  const root=document.documentElement;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const kinds=[['phone','phone'],['tablet','tablet'],['laptop','laptop'],['gaming','controller'],['audio','headphones']];
  let engine,loading=false,failed=false,frame=0,last=0,elapsed=0;
  const active=new Set();
  const sceneCards=[...section.querySelectorAll(".ttra-category-scene")];
  const visibleProduct=()=>entries.some(({card})=>active.has(card));
  const entries=kinds.map(([name,kind])=>{
    const card=section.querySelector(`.ttra-category-${name}`);
    const canvas=document.createElement('canvas');canvas.className='ttra-product-canvas';canvas.setAttribute('aria-hidden','true');card.append(canvas);
    return {card,canvas,kind};
  });
  function allowed(){return !document.hidden && root.dataset.modo==='classic' && !root.classList.contains('ttra-welcome-pending') && !root.classList.contains('ttra-scroll-locked') && !document.body.classList.contains('rc-vista-seccion');}
  function stop(){cancelAnimationFrame(frame);frame=0;last=0;}
  function fallback(){stop();failed=true;engine?.dispose();engine=null;entries.forEach(({card,canvas})=>{card.classList.remove('ttra-3d-ready');canvas.remove();});}
  function draw(){if(!engine||!allowed())return;try{engine.views.forEach(view=>{if(active.has(view.card))engine.render(view,elapsed);});}catch{fallback();}}
  function tick(now){
    frame=0;if(!engine||!visibleProduct()||!allowed()||reduced.matches){last=0;return;}
    if(!last)last=now;
    const interval=innerWidth<=700?1000/24:1000/30;
    if(now-last>=interval){elapsed+=(now-last)/1000;last=now;draw();}
    if(engine)frame=requestAnimationFrame(tick);
  }
  function sync(){stop();sceneCards.forEach(card=>card.classList.toggle('ttra-scene-active',active.has(card)&&allowed()&&!reduced.matches));draw();if(engine&&visibleProduct()&&allowed()&&!reduced.matches)frame=requestAnimationFrame(tick);}
  async function start(){
    if(engine||loading||failed||!allowed())return;
    loading=true;
    try{const {createProductCardScenes}=await import('/product-card-scenes.js');engine=createProductCardScenes(entries);engine.contextCanvas.addEventListener('webglcontextlost',event=>{event.preventDefault();fallback();},{once:true});sync();}
    catch{fallback();}finally{loading=false;}
  }
  const visibility=new IntersectionObserver(changes=>{
    changes.forEach(({target,isIntersecting})=>{if(isIntersecting)active.add(target);else active.delete(target);});
    if(active.size)start();sync();
  },{threshold:0});
  sceneCards.forEach(card=>visibility.observe(card));
  const nearby=new IntersectionObserver(changes=>{if(changes.some(c=>c.isIntersecting))start();},{rootMargin:'200px'});nearby.observe(section);
  const resize=new ResizeObserver(()=>sync());entries.forEach(({canvas})=>resize.observe(canvas));
  reduced.addEventListener('change',sync);
  document.addEventListener('visibilitychange',sync);
  const modeObserver=new MutationObserver(()=>{if(active.size)start();sync();});
  modeObserver.observe(root,{attributes:true,attributeFilter:['class','data-modo']});
  modeObserver.observe(document.body,{attributes:true,attributeFilter:['class']});
  window.addEventListener('pagehide',event=>{stop();if(!event.persisted){visibility.disconnect();nearby.disconnect();resize.disconnect();modeObserver.disconnect();engine?.dispose();engine=null;}});
  window.addEventListener('pageshow',sync);
})();
