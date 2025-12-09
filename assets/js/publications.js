// Main publications page logic
let allPublications = [];
let filteredPublications = [];
let currentFilter = 'all';
let currentSort = 'year-desc';
let searchQuery = '';

const parser = new BibtexParser();

// Load and parse JSON file
async function loadPublications() {
	try {
		const response = await fetch('publications_bib/publications.json');
		allPublications = await response.json();
		
		// Already sorted by year in the JSON file
		
		updateStats();
		filterPublications();
		
		document.getElementById('loading').style.display = 'none';
	} catch (error) {
		console.error('Error loading publications:', error);
		document.getElementById('loading').innerHTML = 
			'<p style="color: #e74c3c;">Error loading publications. Please run: python convert_bib_to_json.py</p>';
	}
}

// Update statistics
function updateStats() {
	const currentYear = new Date().getFullYear();
	const threeYearsAgo = currentYear - 3;
	
	const totalPubs = allPublications.length;
	const articles = allPublications.filter(p => p.type === 'article').length;
	const recentPubs = allPublications.filter(p => {
		const year = parser.extractYear(p);
		return year && year >= threeYearsAgo;
	}).length;
	
	document.getElementById('total-pubs').textContent = totalPubs;
	document.getElementById('total-articles').textContent = articles;
	document.getElementById('recent-pubs').textContent = recentPubs;
}

// Filter publications
function filterPublications() {
	filteredPublications = allPublications.filter(pub => {
		// Type filter
		let matchesType = false;
		if (currentFilter === 'all') {
			matchesType = true;
		} else if (currentFilter === 'with-if') {
			matchesType = parser.extractImpactFactor(pub) !== null;
		} else {
			matchesType = pub.type === currentFilter;
		}
		
		// Search filter
		const matchesSearch = searchQuery === '' || 
			(pub.title && pub.title.toLowerCase().includes(searchQuery)) ||
			(pub.author && pub.author.toLowerCase().includes(searchQuery)) ||
			(pub.keywords && pub.keywords.toLowerCase().includes(searchQuery)) ||
			(pub.journal && pub.journal.toLowerCase().includes(searchQuery)) ||
			(pub.booktitle && pub.booktitle.toLowerCase().includes(searchQuery));
		
		return matchesType && matchesSearch;
	});
	
	// Sort publications
	sortPublications();
	
	renderPublications();
}

// Sort publications
function sortPublications() {
	filteredPublications.sort((a, b) => {
		if (currentSort === 'year-desc') {
			const yearA = parser.extractYear(a) || 0;
			const yearB = parser.extractYear(b) || 0;
			return yearB - yearA;
		} else if (currentSort === 'year-asc') {
			const yearA = parser.extractYear(a) || 0;
			const yearB = parser.extractYear(b) || 0;
			return yearA - yearB;
		} else if (currentSort === 'if-desc') {
			const ifA = parser.extractImpactFactor(a) || 0;
			const ifB = parser.extractImpactFactor(b) || 0;
			return ifB - ifA;
		} else if (currentSort === 'if-asc') {
			const ifA = parser.extractImpactFactor(a) || 0;
			const ifB = parser.extractImpactFactor(b) || 0;
			return ifA - ifB;
		}
		return 0;
	});
}

// Render publications
function renderPublications() {
	const container = document.getElementById('publications-list');
	const noResults = document.getElementById('no-results');
	
	if (filteredPublications.length === 0) {
		container.innerHTML = '';
		noResults.style.display = 'block';
		return;
	}
	
	noResults.style.display = 'none';
	
	let html = '';
	let lastYear = null;
	
	// Only show year dividers if sorting by year
	const showYearDividers = currentSort.startsWith('year');
	
	filteredPublications.forEach(pub => {
		const year = parser.extractYear(pub);
		
		// Add year divider
		if (showYearDividers && year && year !== lastYear) {
			html += `<h3 style="margin-top: 2rem; margin-bottom: 1rem; color: #667eea; font-size: 1.5rem;">${year}</h3>`;
			lastYear = year;
		}
		
		html += renderPublication(pub);
	});
	
	container.innerHTML = html;
}

// Render a single publication
function renderPublication(pub) {
	const title = pub.title || 'Untitled';
	const authors = parser.formatAuthors(pub.author);
	const year = parser.extractYear(pub);
	const impactFactor = parser.extractImpactFactor(pub);
	const type = parser.getTypeLabel(pub.type);
	
	// Determine venue (journal, conference, or school)
	let venue = '';
	if (pub.journal) {
		venue = pub.journal;
		if (pub.volume) venue += `, Vol. ${pub.volume}`;
		if (pub.number) venue += ` (${pub.number})`;
		if (pub.pages) venue += `, pp. ${pub.pages}`;
	} else if (pub.booktitle) {
		venue = pub.booktitle;
	} else if (pub.school) {
		venue = pub.school;
	}
	
	// Determine primary link for title
	let titleLink = '';
	if (pub.doi) {
		titleLink = pub.doi.startsWith('http') ? pub.doi : `https://doi.org/${pub.doi}`;
	} else if (pub.url) {
		titleLink = pub.url;
	}
	
	// Render title with link if available
	const titleHtml = titleLink 
		? `<a href="${titleLink}" target="_blank" rel="noopener noreferrer">${title}</a>`
		: title;
	
	// Build links (secondary)
	let links = '';
	if (pub.url && !pub.doi) {
		// URL is already used in title
	} else if (pub.url && pub.doi) {
		// DOI is in title, show URL as additional link
		links += `<a href="${pub.url}" target="_blank" class="link-btn">
			<i class="fas fa-external-link-alt"></i> View
		</a>`;
	}
	if (pub.doi) {
		// DOI is already in title, but we can keep it as an explicit link too
		const doiUrl = pub.doi.startsWith('http') ? pub.doi : `https://doi.org/${pub.doi}`;
		links += `<a href="${doiUrl}" target="_blank" class="link-btn">
			<i class="fas fa-book"></i> DOI
		</a>`;
	}
	
	// Build badges
	let badges = '';
	if (year) {
		badges += `<span class="year-badge">${year}</span>`;
	}
	badges += `<span class="type-badge">${type}</span>`;
	if (impactFactor) {
		badges += `<span class="impact-badge">IF: ${impactFactor}</span>`;
	}
	
	return `
		<div class="publication-entry">
			<div class="title">${titleHtml}</div>
			<div class="authors">${authors}</div>
			${venue ? `<div class="venue">${venue}</div>` : ''}
			<div class="meta">
				${badges}
			</div>
			${links ? `<div class="links">${links}</div>` : ''}
		</div>
	`;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
	// Load publications
	loadPublications();
	
	// Filter buttons
	document.querySelectorAll('.filter-btn').forEach(btn => {
		btn.addEventListener('click', (e) => {
			const filter = e.target.dataset.filter;
			const sort = e.target.dataset.sort;
			
			if (filter) {
				// Type filter button
				document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
				e.target.classList.add('active');
				currentFilter = filter;
			} else if (sort) {
				// Sort button
				document.querySelectorAll('[data-sort]').forEach(b => b.classList.remove('active'));
				e.target.classList.add('active');
				currentSort = sort;
			}
			
			filterPublications();
		});
	});
	
	// Search input
	const searchInput = document.getElementById('search-input');
	searchInput.addEventListener('input', (e) => {
		searchQuery = e.target.value.toLowerCase();
		filterPublications();
	});
});
