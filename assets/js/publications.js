// Renders publications_bib/publications.json + stats.json (built by build_publications.py
// from the curated CV BibTeX + OpenAlex citation counts). Plain reference list with
// search, type filter and sort. Deep link: publications.html?filter=patent

let allPublications = [];
let currentFilter = 'main';
let currentSort = 'year-desc';
let searchQuery = '';

const TYPE_LABELS = {
	article: 'Journal article', inproceedings: 'Conference paper', incollection: 'Book chapter',
	book: 'Book', phdthesis: 'Thesis', patent: 'Patent', misc: 'Other'
};

function esc(s) {
	return String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

async function loadPublications() {
	const status = document.getElementById('status');
	try {
		const [pubs, stats] = await Promise.all([
			fetch('publications_bib/publications.json').then(r => r.json()),
			fetch('publications_bib/stats.json').then(r => r.ok ? r.json() : {})
		]);
		allPublications = pubs;
		renderStats(stats);
		render();
	} catch (err) {
		console.error(err);
		status.textContent = 'Could not load the publication list.';
	}
}

function renderStats(s) {
	const scholar = s.scholar_h_index !== undefined;
	const cites = scholar ? s.scholar_citations : s.total_citations;
	const h = scholar ? s.scholar_h_index : s.h_index;
	const i10 = scholar ? s.scholar_i10_index : s.i10_index;
	const parts = [
		`${s.total_publications || allPublications.length} scientific outputs`,
		s.articles && `${s.articles} journal articles`,
		s.patents && `${s.patents} patent families`,
		cites && `${cites} citations`,
		h && `h-index ${h}`,
		i10 && `i10-index ${i10}`
	].filter(Boolean);
	let line = parts.join(' · ');
	if (s.last_updated) line += ` (${scholar ? 'Google Scholar' : 'OpenAlex'}, ${s.last_updated})`;
	document.getElementById('stats-line').textContent = line;
}

function year(p) {
	const m = /\d{4}/.exec(p.year || '');
	return m ? +m[0] : 0;
}

function formatAuthors(a) {
	if (!a) return '';
	const list = a.split(/\s+and\s+/i);
	return list.length <= 6 ? list.join(', ') : list.slice(0, 6).join(', ') + ', et al.';
}

function matches(p) {
	const t = p.type;
	const typeOk =
		currentFilter === 'all' ? true :
		currentFilter === 'main' ? (t === 'article' || t === 'patent') :
		currentFilter === 'highly-cited' ? (p.citations || 0) >= 10 :
		t === currentFilter;
	if (!typeOk) return false;
	if (!searchQuery) return true;
	return [p.title, p.author, p.journal, p.booktitle].some(f => (f || '').toLowerCase().includes(searchQuery));
}

function compare(a, b) {
	if (currentSort === 'year-asc') return year(a) - year(b);
	if (currentSort === 'citations-desc') return (b.citations || 0) - (a.citations || 0) || year(b) - year(a);
	return year(b) - year(a);
}

function render() {
	const list = document.getElementById('publications-list');
	const status = document.getElementById('status');
	const pubs = allPublications.filter(matches).sort(compare);

	if (!pubs.length) {
		list.innerHTML = '';
		status.textContent = 'Nothing matches.';
		return;
	}
	status.textContent = `${pubs.length} ${pubs.length === 1 ? 'entry' : 'entries'}`;

	const byYear = currentSort.startsWith('year');
	let html = '', lastYear = null;
	for (const p of pubs) {
		const y = year(p);
		if (byYear && y && y !== lastYear) {
			html += `<li class="pub-year" aria-hidden="true">${y}</li>`;
			lastYear = y;
		}
		html += renderPublication(p, y);
	}
	list.innerHTML = html;
}

function renderPublication(p, y) {
	let venue = p.journal || p.booktitle || '';
	if (p.journal && p.type !== 'patent') {
		if (p.volume) venue += ` ${p.volume}`;
		if (p.number) venue += `(${p.number})`;
		if (p.pages) venue += `, ${p.pages}`;
	}
	const title = p.url
		? `<a href="${esc(p.url)}" rel="noopener">${esc(p.title)}</a>`
		: esc(p.title);
	const meta = [
		p.id && `<span title="${esc(p.category || '')}">${esc(p.id)}</span>`,
		`<span>${TYPE_LABELS[p.type] || esc(p.type)}${y ? ', ' + y : ''}</span>`,
		p.citations > 0 && `<span>${p.citations} citation${p.citations === 1 ? '' : 's'}</span>`,
		p.url && `<a href="${esc(p.url)}" rel="noopener">${p.type === 'patent' ? 'Google Patents' : 'DOI'}</a>`
	].filter(Boolean).join('');
	return `<li class="pub">
		<div class="title">${title}</div>
		<div class="authors">${esc(formatAuthors(p.author))}</div>
		${venue ? `<div class="venue">${esc(venue)}</div>` : ''}
		<div class="meta">${meta}</div>
	</li>`;
}

document.addEventListener('DOMContentLoaded', () => {
	const wanted = new URLSearchParams(location.search).get('filter');
	if (wanted && document.querySelector(`[data-filter="${wanted}"]`)) currentFilter = wanted;

	document.querySelectorAll('.choices button').forEach(btn => {
		const key = btn.dataset.filter ? 'filter' : 'sort';
		if (btn.dataset[key] === (key === 'filter' ? currentFilter : currentSort)) {
			btn.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('active'));
			btn.classList.add('active');
		}
		btn.addEventListener('click', () => {
			btn.parentElement.querySelectorAll('button').forEach(b => b.classList.remove('active'));
			btn.classList.add('active');
			if (key === 'filter') currentFilter = btn.dataset.filter; else currentSort = btn.dataset.sort;
			render();
		});
	});

	document.getElementById('search-input').addEventListener('input', e => {
		searchQuery = e.target.value.trim().toLowerCase();
		render();
	});

	loadPublications();
});
