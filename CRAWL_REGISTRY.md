# Macau Events — Crawler Registry

> **This is the control panel.** Enable or disable any source by changing `enabled` to `true` or `false`.
> The AI crawler reads this file first on every run to build its task list.
> For full details on a source (selectors, HTML structure, notes), open its linked file.

---

## How to add a new source

1. Copy the template row at the bottom into the correct section
2. Set `enabled: true`
3. Create a detail file in `sources/<type>/<domain>.md` (copy `sources/TEMPLATE.md`)
4. The crawler picks it up on the next run automatically

---

## Government & Cultural — Tier 1 (Daily)

| enabled | source | domain | primary url | detail |
|---------|--------|---------|-------------|--------|
| true | Macao Government Tourism Office | macaotourism.gov.mo | https://www.macaotourism.gov.mo/en/events/calendar | [view](sources/government/macaotourism.gov.mo.md) |
| true | Cultural Affairs Bureau (ICM) | icm.gov.mo | https://www.icm.gov.mo/en/events/calendar | [view](sources/government/icm.gov.mo.md) |
| true | Macao Cultural Centre (CCM) | macaucci.gov.mo | https://www.macaucci.gov.mo/en/events | [view](sources/government/macaucci.gov.mo.md) |
| true | Macao Museum of Art (MAM) | mam.gov.mo | https://www.mam.gov.mo/en/exhibitions/ | [view](sources/government/mam.gov.mo.md) |
| true | Macao Public Library | library.gov.mo | https://www.library.gov.mo/en/promotion-events | [view](sources/government/library.gov.mo.md) |


---

## Casino Resorts — Tier 2 (Daily)

| enabled | source | domain | primary url | detail |
|---------|--------|---------|-------------|--------|
| true | Galaxy Macau | galaxymacau.com | https://www.galaxymacau.com/ticketing/event-list/ | [view](sources/casinos/galaxymacau.com.md) |
| true | Sands / Venetian Macao | sandsresortsmacao.com | https://en.sandsresortsmacao.com/sands-lifestyle/events-ent.html | [view](sources/casinos/sandsresortsmacao.com.md) |
| true | Wynn Resorts Macao | wynnresortsmacau.com | https://www.wynnresortsmacau.com/en/wynn-palace/offers | [view](sources/casinos/wynnmacau.com.md) |
| true | City of Dreams / Studio City | cityofdreamsmacau.com | https://www.cityofdreamsmacau.com/en/events | [view](sources/casinos/cityofdreamsmacau.com.md) |
| true | MGM Macau / MGM Cotai | mgm.mo | https://www.mgm.mo/en/entertainment | [view](sources/casinos/mgm.mo.md) |
| true | Grand Lisboa / SJM | sjmresorts.com | https://www.sjmresorts.com/en/happenings | [view](sources/casinos/grandlisboahotels.com.md) |

---

## Venues & Nightlife — Tier 3 (Weekly)

| enabled | source | domain | primary url | detail |
|---------|--------|---------|-------------|--------|
| true | Cuba Macao | cubamacao.com | https://www.cubamacao.com | [view](sources/venues/cuba-macao.md) |
| true | Sky 21 | sky21.com.mo | https://www.sky21.com.mo | [view](sources/venues/sky21.md) |
| true | Bob Bar | bobbarmacau.com | https://www.bobbarmacau.com | [view](sources/venues/bob-bar.md) |
| false | La Ferrari | laferrari.com.mo | https://www.laferrari.com.mo | [view](sources/venues/laferrari.md) |
| false | Central Macau | centralmacau.com | https://www.centralmacau.com | [view](sources/venues/central-macau.md) |
| false | The Den | thedenmacau.com | https://www.thedenmacau.com | [view](sources/venues/the-den.md) |
| true | Fisherman's Wharf | fishermanswharf.com.mo | https://www.fishermanswharf.com.mo/whats-on/ | [view](sources/venues/fishermans-wharf.md) |


---

## Media & Promoters — Tier 3 (Weekly)

| enabled | source | domain | primary url | detail |
|---------|--------|---------|-------------|--------|
| true | Macau Daily Times | macaudailytimes.com.mo | https://www.macaudailytimes.com.mo | [view](sources/promoters/macaudailytimes.com.mo.md) |
| true | TDM | tdm.com.mo | https://www.tdm.com.mo | [view](sources/promoters/tdm.md) |
| true | Inside Asian Living | insideasianliving.com | https://www.insideasianliving.com | [view](sources/promoters/inside-asian-living.md) |
| true | Macau Lifestyle | macaulifestyle.com | https://www.macaulifestyle.com | [view](sources/promoters/macau-lifestyle.md) |
| false | Macau News | macaunews.mo | https://www.macaunews.mo | [view](sources/promoters/macaunews.md) |

---

## Add a new source — copy this row

```
| true | Source Name | domain.com | https://domain.com/events | [view](sources/<type>/<domain>.md) |
```

Then create `sources/<type>/<domain>.md` — see `sources/TEMPLATE.md` for the format.

---

## Stats (auto-updated by crawler)

- Last registry update: 2026-09-10
- Total sources: 22  |  Enabled: 18  |  Disabled: 4
- Tier 1 (daily govt): 5  |  Tier 2 (daily casinos): 6  |  Tier 3 (weekly): 11
