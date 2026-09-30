"""Safety content endpoints.

Serves pictorial + textual (and optionally audio) safety guidance, localized.
Content is safe to cache offline: it changes rarely and is small.
"""

from fastapi import APIRouter, Depends, Query

from ..auth import Principal, get_principal
from ..db import get_db

router = APIRouter()


async def _fetch_topics(conn, locale: str, category_ids: list[str] | None) -> list[dict]:
    params: list = [locale, locale]
    category_filter = ""
    if category_ids:
        category_filter = (
            "AND EXISTS (SELECT 1 FROM safety_topic_category_links stc "
            "WHERE stc.topic_id = st.id AND stc.material_category_id = ANY(%s::uuid[]))"
        )
        params.append(category_ids)

    cur = await conn.execute(
        f"""
        SELECT st.id::text, st.code, st.severity, st.sort_order,
               COALESCE(i.title, st.title) AS title,
               i.short_text, i.do_text, i.dont_text, i.audio_url,
               COALESCE(
                   (SELECT jsonb_agg(jsonb_build_object(
                        'kind', p.kind, 'icon_key', p.icon_key
                    ) ORDER BY p.sort_order)
                    FROM safety_pictograms p WHERE p.topic_id = st.id),
                   '[]'::jsonb
               ) AS pictograms
        FROM safety_topics st
        LEFT JOIN safety_topic_i18n i
               ON i.topic_id = st.id AND i.locale = %s
        WHERE st.is_active
          AND EXISTS (
              SELECT 1 FROM safety_topic_i18n x
              WHERE x.topic_id = st.id AND x.locale = %s
          )
          {category_filter}
        ORDER BY
            CASE st.severity
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
            END,
            st.sort_order
        """,
        params,
    )
    rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "code": r[1],
            "severity": r[2],
            "title": r[4],
            "short_text": r[5],
            "do_text": r[6],
            "dont_text": r[7],
            "audio_url": r[8],
            "pictograms": r[9],
        }
        for r in rows
    ]


@router.get("/safety/topics")
async def list_safety_topics(
    locale: str = Query("en"),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """All active safety topics, localized, ordered by severity."""
    topics = await _fetch_topics(conn, locale, None)
    return {"locale": locale, "count": len(topics), "topics": topics}


@router.get("/safety/for-categories")
async def safety_for_categories(
    category_ids: list[str] = Query(...),
    locale: str = Query("en"),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Contextual warnings for the materials in a collector's lot.

    Used on the capture screen: a collector photographing a battery is shown
    battery-handling safety guidance before they continue.
    """
    topics = await _fetch_topics(conn, locale, category_ids)
    return {"locale": locale, "count": len(topics), "topics": topics}


@router.get("/safety/audio-availability")
async def audio_availability(
    locale: str = Query("en"),
    principal: Principal = Depends(get_principal),
    conn=Depends(get_db),
) -> dict:
    """Which topics have voice assets in the requested locale.

    Lets the client show a play button only where audio actually exists, rather
    than rendering a dead control — important for low-literacy users who cannot
    read the text at all.
    """
    cur = await conn.execute(
        """
        SELECT st.code, a.cloudinary_url, a.duration_seconds, a.is_complete
        FROM safety_topics st
        LEFT JOIN safety_audio_assets a
               ON a.topic_id = st.id AND a.locale = %s
        WHERE st.is_active
        ORDER BY st.sort_order
        """,
        (locale,),
    )
    rows = await cur.fetchall()
    available = [r[0] for r in rows if r[1] is not None]
    return {
        "locale": locale,
        "total_topics": len(rows),
        "audio_available": len(available),
        "coverage": round(len(available) / len(rows), 2) if rows else 0.0,
        "topics": [
            {
                "code": r[0],
                "audio_url": r[1],
                "duration_seconds": float(r[2]) if r[2] is not None else None,
                "is_complete": r[3],
            }
            for r in rows
        ],
    }
