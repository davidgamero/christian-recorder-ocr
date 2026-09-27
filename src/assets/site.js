/* Shared search URLs and source-safe text highlighting. No OCR is parsed as HTML. */
document.querySelectorAll('.load-original').forEach(button=>button.addEventListener('click',async()=>{
  button.disabled=true;
  const output=button.nextElementSibling;
  try{const r=await fetch(button.dataset.url);if(!r.ok)throw Error(`HTTP ${r.status}`);output.textContent=await r.text();button.textContent='Original OCR loaded';}
  catch(e){output.textContent=`Could not load original text: ${e.message}`;button.disabled=false;}
}));

const queryFromURL=()=>new URL(location.href).searchParams.get('q')||'';
const filtersPanel=document.getElementById('search-filters');
if(filtersPanel)filtersPanel.open=!window.matchMedia('(max-width: 700px)').matches;
const withQuery=(href,query)=>{
  const url=new URL(href,location.href);
  if(query)url.searchParams.set('q',query);else url.searchParams.delete('q');
  return url;
};

function initSearch(){
  const input=document.querySelector('pagefind-input');
  if(!input)return;
  const manager=window.PagefindComponents?.getInstanceManager();
  if(!manager)return;
  const instance=manager.getInstance('default');
  let query=queryFromURL();
  const intro=document.getElementById('project-intro');
  let searching=Boolean(query.trim());
  if(intro)intro.open=!searching;
  const results=document.querySelector('pagefind-results');
  function decorateResults(){
    results.querySelectorAll('.search-result h3 a').forEach(a=>{
      const url=new URL(a.href,location.href);
      if(url.origin===location.origin)a.href=withQuery(a.href,query).href;
    });
  }
  new MutationObserver(decorateResults).observe(results,{childList:true,subtree:true});
  instance.on('search',term=>{
    query=term||'';
    const nextSearching=Boolean(query.trim());
    if(intro&&nextSearching!==searching)intro.open=!nextSearching;
    searching=nextSearching;
    const url=withQuery(location.href,query);
    if(url.href!==location.href)history.replaceState(null,'',url);
    decorateResults();
  },input);
  const restore=()=>{
    query=queryFromURL();
    const field=input.querySelector('input');
    if(field){field.value=query;field.dispatchEvent(new Event('input',{bubbles:true}));}
    instance.triggerSearch(query);
    decorateResults();
  };
  window.addEventListener('popstate',restore);
  if(query)restore();
}

function highlightDocument(){
  const text=document.querySelector('.transcription');
  const bar=document.getElementById('match-navigation');
  if(!text||!bar)return;
  const blocks=[...text.querySelectorAll('.paragraph-text')];
  if(!blocks.length)blocks.push(text);
  const originals=blocks.map(block=>block.textContent);
  function update(){
    const query=queryFromURL();
    blocks.forEach((block,i)=>{block.textContent=originals[i];});
    bar.querySelector('.query-tools').hidden=!query;
    if(!query)return;
    document.getElementById('match-query').textContent=query;
    const back=document.getElementById('back-to-search');
    back.href=withQuery(back.href,query).href;
    // Keep context when using previous/next scan links, too.
    document.querySelectorAll('main a').forEach(a=>{
      const target=new URL(a.href,location.href);
      if(target.origin===location.origin&&target.pathname.includes('/scans/')&&target.pathname.endsWith('/'))a.href=withQuery(a.href,query).href;
    });
    // Quoted strings are phrases; other Unicode word tokens match individually.
    // These are literal matches, not Pagefind's stemmed/fuzzy retrieval matches.
    const parts=[];
    for(const match of query.matchAll(/"([^"]+)"|([\p{L}\p{N}]+(?:['’’-][\p{L}\p{N}]+)*)/gu)){
      const part=(match[1]||match[2]).trim();
      if(part)parts.push(part);
    }
    const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const alternatives=[...new Set(parts)].sort((a,b)=>b.length-a.length).map(s=>s.split(/\s+/).map(escape).join('\\s+'));
    const marks=[];
    if(alternatives.length){
      const pattern=new RegExp('(?<![\\p{L}\\p{N}])(?:'+alternatives.join('|')+')(?![\\p{L}\\p{N}])','giu');
      blocks.forEach((block,i)=>{
        const original=originals[i],fragment=document.createDocumentFragment();
        let offset=0;
        for(const match of original.matchAll(pattern)){
          fragment.append(document.createTextNode(original.slice(offset,match.index)));
          const mark=document.createElement('mark');
          mark.className='query-match';mark.textContent=match[0];mark.tabIndex=-1;
          fragment.append(mark);marks.push(mark);offset=match.index+match[0].length;
        }
        fragment.append(document.createTextNode(original.slice(offset)));
        block.replaceChildren(fragment);
      });
    }
    let current=-1;
    const count=document.getElementById('match-count');
    const prev=document.getElementById('match-prev'),next=document.getElementById('match-next');
    prev.disabled=next.disabled=!marks.length;
    document.getElementById('match-note').textContent=marks.length?'Exact text matches; search may also match word variants.':'No exact text matches. Search may have matched a word variant.';
    const jump=(index,focus=true)=>{
      if(!marks.length){count.textContent='0 matches';return;}
      if(current>=0)marks[current].classList.remove('current-match');
      current=(index+marks.length)%marks.length;
      marks[current].classList.add('current-match');
      count.textContent=`${current+1} of ${marks.length} matches`;
      marks[current].scrollIntoView({block:'center',behavior:'instant'});
      if(focus)marks[current].focus({preventScroll:true});
    };
    prev.onclick=()=>jump(current-1);
    next.onclick=()=>jump(current+1);
    jump(0,false);
  }
  window.addEventListener('popstate',update);
  update();
}

// Pagefind is a module; wait until its component registration is complete.
if(document.querySelector('pagefind-input'))customElements.whenDefined('pagefind-input').then(initSearch);
highlightDocument();
