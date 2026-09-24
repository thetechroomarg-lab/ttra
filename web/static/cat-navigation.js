// Persistent storefront host: keep the original masthead and mascot mounted.
// Child documents retain their page-specific scripts, forms and menus.
export function persistentNavigation({attach,portal}) {
  const header=document.querySelector("body > header");
  let pageObserver=null;
  const profileSelector=".rc-perfil-boton, .ttra-site-profile";
  header.addEventListener("click",event=>{
    if(!frame || !event.target.closest(profileSelector))return;
    event.preventDefault();event.stopImmediatePropagation();
    frame.contentDocument?.querySelector(profileSelector)?.click();
  },true);
  let frame=null,pending=null,timeout=0,first=true,lastDocument=null;
  document.addEventListener('keydown',event=>{
    if(frame&&event.key==='Escape')frame.contentDocument?.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
  });
  const bound=new WeakSet();
  const supported=url=>url.origin===location.origin && !url.searchParams.has('embed') &&
    /^(\/|\/catalogo\/?|\/comparativa\/?|\/vaiven\/?|\/bitu\/?|\/fendi\/?|\/login(?:\.html)?|\/perfil(?:\.html)?|\/p\/[^/]+)$/.test(url.pathname);
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
      if(url.href===doc.location.href){event.preventDefault();doc.defaultView.scrollTo({top:0,behavior:'smooth'});return;}
      event.preventDefault();navigate(url,'push');
    });
  }
  async function loaded() {
    let doc,url;
    try{doc=frame.contentDocument;url=new URL(frame.contentWindow.location.href);}catch{return;}
    if(!doc||url.href==='about:blank'||doc===lastDocument)return;
    if(!supported(url)||!doc.querySelector('body > header, body.vaiven-page #vaiven-album, body.bitu-page #bitu-album, body.fendi-page #fendi-album')) {
      // Unsupported/error documents fall back to ordinary full-page navigation.
      const target=pending?.url||url;pending=null;location.assign(target.href);return;
    }
    lastDocument=doc;
    clearTimeout(timeout);
    const transaction=pending;pending=null;
    const album=doc.body.classList.contains('vaiven-page')||doc.body.classList.contains('bitu-page')||doc.body.classList.contains('fendi-page');
    document.documentElement.classList.toggle('ttra-shell-album',album);
    doc.documentElement.classList.add('ttra-shell-content');
    const sync=()=>{
      const theme=doc.documentElement.dataset.classicTheme||'dark';
      document.documentElement.dataset.classicTheme=theme;
      const source=doc.querySelector('.ttra-site-rate');
      const rate=header.querySelector('.ttra-site-rate');
      if(source&&rate)rate.innerHTML=source.innerHTML;
      if(rate)rate.hidden=url.pathname==='/';
      const initials=header.querySelector('.rc-perfil-nombre, .ttra-site-initials');
      const initialsText=doc.querySelector('.rc-perfil-nombre, .ttra-site-initials')?.textContent||'';
      if(initials&&initials.textContent!==initialsText)initials.textContent=initialsText;
      const expanded=doc.querySelector(profileSelector)?.getAttribute('aria-expanded')==='true';
      header.querySelector(profileSelector)?.setAttribute('aria-expanded',String(expanded));
    };
    pageObserver?.disconnect();pageObserver=new MutationObserver(sync);
    pageObserver.observe(doc.documentElement,{attributes:true,attributeFilter:['data-classic-theme']});
    const account=doc.querySelector('.ttra-header-account');
    if(account)pageObserver.observe(account,{subtree:true,attributes:true,childList:true,characterData:true});
    sync();
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
    try{sessionStorage.setItem("ttra_portada_vista","1");}catch{}
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
  return {accepts:doc=>doc===document||doc.defaultView===frame?.contentWindow,bind,ready:doc=>{if(doc===frame?.contentDocument)loaded();}};
}
