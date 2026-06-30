import { getJobs, getSources, sendJson } from './_store.js';

function canonicalUrl(url) {
  try {
    const parsed = new URL(url);
    parsed.hash = '';
    return parsed.toString().replace(/\/$/, '').toLowerCase();
  } catch (_) {
    return String(url || '').trim().toLowerCase();
  }
}

function sourceType(job) {
  const text = `${job.source || ''} ${job.channel || ''} ${job.url || ''}`.toLowerCase();
  if (text.includes('linkedin')) return 'manual_login';
  if (text.includes('getonboard') || text.includes('get on board')) return 'public_listing';
  if (text.includes('we work remotely') || text.includes('weworkremotely') || text.includes('remotive')) return 'remote_board';
  if (text.includes('trabajando')) return 'public_listing';
  if (text.includes('aira') || text.includes('airavirtual')) return 'public_direct';
  if (text.includes('manual') || text.includes('dashboard')) return 'manual_entry';
  return job.url ? 'company_careers' : 'unknown';
}

function countBy(items, fn) {
  return items.reduce((acc, item) => {
    const key = fn(item) || 'sin dato';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

export function acquisitionPayload() {
  const jobs = getJobs();
  const sources = getSources();
  const normalized = jobs.map(job => ({
    id: job.id,
    canonical_url: canonicalUrl(job.url),
    source_name: job.source || 'unknown',
    source_type: sourceType(job),
    channel: job.channel,
    company: job.company,
    role: job.role,
    score: job.score || 0,
    status: job.status || 'new',
    description_chars: (job.description || '').length,
    url: job.url
  }));
  const duplicateUrls = Object.values(countBy(normalized.filter(j => j.canonical_url), j => j.canonical_url)).filter(count => count > 1).length;
  const listingLike = normalized.filter(job => ['Get on Board', 'Trabajando'].includes(job.company) || /jobs \| get on board|portal de empleo/i.test(job.role || ''));
  const sourceRows = Object.entries(countBy(normalized, j => j.source_name)).map(([name, count]) => {
    const items = normalized.filter(job => job.source_name === name);
    return {
      name,
      type: items[0] ? items[0].source_type : 'unknown',
      configured: false,
      configured_url: '',
      login_required: items.some(job => job.source_type === 'manual_login'),
      jobs: count,
      new: items.filter(job => job.status === 'new').length,
      prepared: items.filter(job => job.status === 'prepared').length,
      avg_score: Math.round(items.reduce((sum, job) => sum + job.score, 0) / Math.max(1, items.length) * 10) / 10,
      top_jobs: items.sort((a, b) => b.score - a.score).slice(0, 5)
    };
  }).sort((a, b) => b.jobs - a.jobs);
  return {
    generated_at: new Date().toISOString(),
    storage: {
      kind: 'vercel_memory_demo',
      path: 'in-memory demo store',
      size_bytes: 0,
      db: false,
      note: 'En Vercel esto es demo en memoria. La adquisición real y persistente corre localmente.'
    },
    summary: {
      jobs: jobs.length,
      configured_sources: (sources.searches || []).length,
      target_companies: 0,
      company_links: (sources.company_links || []).length,
      last_scan_at: null,
      last_scan_added: 0,
      last_scan_updated: 0,
      last_scan_events: 0,
      last_scan_errors: 0
    },
    counts: {
      by_channel: countBy(normalized, j => j.channel),
      by_source: countBy(normalized, j => j.source_name),
      by_source_type: countBy(normalized, j => j.source_type),
      by_status: countBy(normalized, j => j.status)
    },
    sources: sourceRows,
    normalization: {
      current_state: 'Demo normalizado en memoria; en local la data real está en JSON.',
      recommended_next: 'Migrar la adquisición real local a SQLite con jobs, sources, scans, scan_events y raw_observations.'
    },
    quality: {
      duplicate_canonical_urls: duplicateUrls,
      listing_like_jobs: listingLike.length,
      missing_or_short_descriptions: normalized.filter(job => job.description_chars < 280).length,
      sample_listing_like_jobs: listingLike.slice(0, 10),
      sample_missing_detail_jobs: normalized.filter(job => job.description_chars < 280).slice(0, 10)
    }
  };
}

export default function handler(req, res) {
  return sendJson(res, acquisitionPayload());
}
