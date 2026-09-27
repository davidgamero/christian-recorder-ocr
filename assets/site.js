document.querySelectorAll('.load-original').forEach(button=>button.addEventListener('click',async()=>{
  button.disabled=true;
  const output=button.nextElementSibling;
  try{const r=await fetch(button.dataset.url);if(!r.ok)throw Error(`HTTP ${r.status}`);output.textContent=await r.text();button.textContent='Original OCR loaded';}
  catch(e){output.textContent=`Could not load original text: ${e.message}`;button.disabled=false;}
}));
