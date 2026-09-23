// Opt-in persistent host: each storefront document keeps its own scripts and
// forms while the mascot's single animation loop lives in the top document.
export function persistentNavigation({active,attach,portal}) {
  let frame=null,pending=null,timeout=0,first=true;
  const bound=new WeakSet();
  const supported=url=>url.origin===location.origin && !url.searchParams.has('embed') &&
    /^(\/|\/catalogo\/?|\/vaiven\/?|\/login(?:\.html)?|\/perfil(?:\.html)?|\/p\/[^/]+)$/.test(url.pathname);
  const safeURL=url=>url.pathname+url.search+(/token|password|code=/i.test(url.hash)?'':url.hash);
  function bind(doc) {
    if(bound.has(doc))return;bound.add(doc);
    doc.addEventListener('click',event=>{
      const link=event.target.closest?.('a[href]');
      if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.download||link.target&&link.target!=='_self')return;
      const url=new URL(link.href,doc.location.href);
      // Current-page anchors (including the catalog's search focus handler)
      // retain their native behavior. Run in the bubbling phase after controls.
      if(url.pathname===doc.location.pathname&&url.search===doc.location.search&&url.hash)return;
      if(!supported(url)){if(frame && url.origin!==location.origin && /^https?:$/.test(url.protocol)){event.preventDefault();location.assign(url.href);}return;}
      if(!active()) {
        if(frame){event.preventDefault();location.assign(url.href);}return;
      }
      event.preventDefault();navigate(url,'push');
    });
  }
  async function loaded() {
    let doc,url;
    try{doc=frame.contentDocument;url=new URL(frame.contentWindow.location.href);}catch{return;}
    if(!doc||url.href==='about:blank')return;
    if(!supported(url)||!doc.querySelector('body > header, body.vaiven-page #vaiven-album')) {
      // Unsupported/error documents fall back to ordinary full-page navigation.
      const target=pending?.url||url;pending=null;location.assign(target.href);return;
    }
    clearTimeout(timeout);
    const transaction=pending;pending=null;
    await attach(doc);bind(doc);
    if(first){
      const oldY=scrollY;
      history.replaceState({...history.state,ttraCatShell:true,scrollY:oldY},'',location.href);
      first=false;document.documentElement.classList.add('ttra-cat-shell');
      document.body.classList.add('rc-vista-seccion');
    }
    frame.style.visibility='visible';frame.removeAttribute('aria-busy');
    document.title=doc.title;
    if(transaction?.mode==='push')history.pushState({ttraCatShell:true,scrollY:0},'',safeURL(url));
    else if(transaction?.mode!=='pop')history.replaceState({...history.state,ttraCatShell:true},'',safeURL(url));
    if(transaction?.mode==='pop')frame.contentWindow.scrollTo(0,transaction.scrollY||0);
    frame.focus();
    portal.removeAttribute('data-loading');
  }
  function navigate(url,mode,scrollY=0) {
    if(frame?.contentWindow && !pending && mode!=='pop') {
      history.replaceState({...history.state,scrollY:frame.contentWindow.scrollY},'',location.href);
    }
    pending={url,mode,scrollY};portal.dataset.loading='true';
    if(!frame){
      frame=document.createElement('iframe');frame.id='ttra-storefront-frame';frame.title='The Tech Room Arg · Tienda';
      frame.style.visibility='hidden';
      frame.addEventListener('load',loaded);document.body.append(frame);frame.src=url.href;
    } else frame.contentWindow.location.replace(url.href);
    frame.setAttribute('aria-busy','true');
    clearTimeout(timeout);timeout=setTimeout(()=>{
      // Preserve a usable route if a document cannot load into the host.
      if(pending)location.assign(pending.url.href);
    },25000);
  }
  window.addEventListener('popstate',event=>{
    if(!frame)return;
    const url=new URL(location.href);
    if(supported(url))navigate(url,'pop',event.state?.scrollY||0);
    else location.assign(url.href);
  });
  bind(document);
  return {accepts:doc=>doc===document||doc.defaultView===frame?.contentWindow,bind};
}
