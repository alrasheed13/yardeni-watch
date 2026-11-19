"""Public RSS headlines for Yardeni QuickTakes (not a paid-content reader).

Only headline, link, publication date and a short description are retained.
No claims that RSS text reflects a current verified numerical market indicator.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET

FEED_URL = 'https://www.yardeniquicktakes.com/rss/'
HOSTS = {'www.yardeniquicktakes.com', 'yardeniquicktakes.com'}


def clean_text(s: str, limit: int = 185) -> str:
    s = html.unescape(re.sub(r'<[^>]*>', ' ', str(s or '')))
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:limit].rstrip() + ('…' if len(s) > limit else '')


def parse_rss(blob: bytes | str, max_items: int = 10) -> list[dict]:
    if isinstance(blob, bytes):
        if len(blob) > 2_000_000:
            raise ValueError('RSS larger than 2MB')
    root = ET.fromstring(blob)
    if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed'):
        raise ValueError('Not a supported RSS/Atom document')
    is_atom = root.tag != 'rss'
    node_list = root.findall('{http://www.w3.org/2005/Atom}entry') if is_atom else root.findall('./channel/item')
    out=[]
    for item in node_list:
        if is_atom:
            ns='{http://www.w3.org/2005/Atom}'
            title=item.findtext(ns+'title','')
            link=next((x.get('href','') for x in item.findall(ns+'link') if x.get('rel','alternate') == 'alternate'), '')
            published=item.findtext(ns+'published','') or item.findtext(ns+'updated','')
            summary=item.findtext(ns+'summary','')
            categories=[x.get('term','') for x in item.findall(ns+'category')]
        else:
            title=item.findtext('title','')
            link=item.findtext('link','')
            published=item.findtext('pubDate','')
            summary=item.findtext('description','')
            categories=[x.text or '' for x in item.findall('category')]
        url=urllib.parse.urlsplit(link.strip())
        if url.scheme!='https' or (url.hostname or '').lower() not in HOSTS:
            continue
        if not title.strip():continue
        if published:
            try:
                pub_dt=(dt.datetime.fromisoformat(published.replace('Z','+00:00')) if is_atom
                        else email.utils.parsedate_to_datetime(published))
                published=pub_dt.date().isoformat()
            except (ValueError,TypeError):published=None
        else:published=None
        labels={s.strip().lower() for s in categories}
        # Do not assert that a full article is readable from the public feed.
        access=('Paid' if 'paid' in labels else 'Public' if 'public' in labels else 'Unspecified')
        out.append({'title':clean_text(title,140),'url':link.strip(),
                    'published':published, 'summary':clean_text(summary),
                    'access':access})
        if len(out)>=max_items:break
    if not out:raise ValueError('RSS has no usable links to Yardeni QuickTakes')
    return out
