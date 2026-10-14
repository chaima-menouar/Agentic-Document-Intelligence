import React from 'react';
export function Mark(){return <svg className="clario-mark" viewBox="0 0 48 48" fill="none" aria-hidden="true"><rect width="48" height="48" rx="15" fill="currentColor"/><path d="M32 15a12 12 0 1 0 0 18" stroke="white" strokeWidth="4" strokeLinecap="round"/><path d="m23 24 5 5 10-12" stroke="white" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"/><circle cx="36" cy="12" r="2" fill="#ffceae"/></svg>}
export function Brand(){return <><Mark/><span className="clario-wordmark">clario<span className="brand-sub">Document intelligence</span></span></>}
export function Glyph({name,size=20}){const paths={
mic:<><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/></>,
stop:<rect x="5" y="5" width="14" height="14" rx="3"/>,
volume:<><path d="m11 4-6 5H2v6h3l6 5zM15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/></>,
file:<><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></>,
spark:<><path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3Z"/><path d="M20 2v4m-2-2h4"/></>,
check:<path d="m5 12 4 4L19 6"/>,
shield:<><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/></>,
external:<><path d="M14 4h6v6m0-6L10 14"/><path d="M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/></>,
arrow:<path d="M4 12h16m-6-6 6 6-6 6"/>,up:<path d="M12 20V4m-6 6 6-6 6 6"/>,
play:<path d="m8 4 12 8-12 8z"/>,
plus:<path d="M12 5v14M5 12h14"/>,
info:<><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/></>,
sun:<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></>,
moon:<path d="M20 14A8.5 8.5 0 0 1 10 4a8.5 8.5 0 1 0 10 10Z"/>,
workflow:<><rect x="3" y="3" width="6" height="6" rx="2"/><rect x="15" y="15" width="6" height="6" rx="2"/><path d="M9 6h6a3 3 0 0 1 3 3v6M6 9v9h9"/></>
};return <svg className={`ui-glyph glyph-${name}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]||paths.file}</svg>}
