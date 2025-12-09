// Simple BibTeX parser
class BibtexParser {
	parse(bibtexString) {
		const entries = [];
		// Match each BibTeX entry
		const entryRegex = /@(\w+)\s*\{\s*([^,]+)\s*,\s*([\s\S]*?)(?=\n@|\n*$)/g;
		let match;

		while ((match = entryRegex.exec(bibtexString)) !== null) {
			const type = match[1].toLowerCase();
			const key = match[2].trim();
			const content = match[3];

			const entry = {
				type: type,
				key: key,
				...this.parseFields(content)
			};

			entries.push(entry);
		}

		return entries;
	}

	parseFields(content) {
		const fields = {};
		// Match field = {value} or field = "value"
		const fieldRegex = /(\w+)\s*=\s*\{((?:[^{}]|\{[^}]*\})*)\}|(\w+)\s*=\s*"([^"]*)"/g;
		let match;

		while ((match = fieldRegex.exec(content)) !== null) {
			const fieldName = (match[1] || match[3]).toLowerCase();
			let fieldValue = match[2] || match[4];
			
			// Clean up the value
			fieldValue = this.cleanLatex(fieldValue);
			fields[fieldName] = fieldValue;
		}

		return fields;
	}

	cleanLatex(text) {
		if (!text) return '';
		
		// Remove LaTeX commands but preserve content
		text = text.replace(/\\textbf\{([^}]*)\}/g, '<strong>$1</strong>');
		text = text.replace(/\\textit\{([^}]*)\}/g, '<em>$1</em>');
		text = text.replace(/\{\\textbf\s*([^}]*)\}/g, '<strong>$1</strong>');
		text = text.replace(/\\text\{([^}]*)\}/g, '$1');
		
		// Handle accented characters
		text = text.replace(/\\'\{e\}/g, 'é');
		text = text.replace(/\\'e/g, 'é');
		text = text.replace(/\\`\{e\}/g, 'è');
		text = text.replace(/\\\^\{e\}/g, 'ê');
		text = text.replace(/\\"\{e\}/g, 'ë');
		text = text.replace(/\\c\{c\}/g, 'ç');
		text = text.replace(/\\~\{a\}/g, 'ã');
		text = text.replace(/\\~\{o\}/g, 'õ');
		text = text.replace(/\\'\{a\}/g, 'á');
		text = text.replace(/\\'\{o\}/g, 'ó');
		text = text.replace(/\\'\{i\}/g, 'í');
		text = text.replace(/\\"\{o\}/g, 'ö');
		text = text.replace(/\{\\"o\}/g, 'ö');
		text = text.replace(/\{\\"u\}/g, 'ü');
		
		// Handle special characters
		text = text.replace(/---/g, '—');
		text = text.replace(/--/g, '–');
		text = text.replace(/``/g, '"');
		text = text.replace(/''/g, '"');
		
		// Remove remaining braces that are just for grouping
		text = text.replace(/\{([^{}]*)\}/g, '$1');
		
		// Clean up extra whitespace
		text = text.replace(/\s+/g, ' ').trim();
		
		return text;
	}

	extractYear(entry) {
		if (entry.year) {
			// Extract just the number from potential bold/formatting
			const match = entry.year.match(/(\d{4})/);
			return match ? parseInt(match[1]) : null;
		}
		return null;
	}

	extractImpactFactor(entry) {
		if (entry.note) {
			const match = entry.note.match(/FI:\s*([\d.]+)/i);
			return match ? parseFloat(match[1]) : null;
		}
		return null;
	}

	formatAuthors(authors) {
		if (!authors) return '';
		
		// Split by 'and' but be careful with accented characters
		const authorList = authors.split(/\s+and\s+/i);
		
		// Clean each author name
		const cleanedAuthors = authorList.map(author => {
			// Remove extra braces and clean
			author = this.cleanLatex(author);
			return author.trim();
		});
		
		if (cleanedAuthors.length <= 3) {
			return cleanedAuthors.join(', ');
		} else {
			return cleanedAuthors.slice(0, 3).join(', ') + ', et al.';
		}
	}

	getTypeLabel(type) {
		const labels = {
			'article': 'Journal Article',
			'inproceedings': 'Conference Paper',
			'incollection': 'Book Chapter',
			'book': 'Book',
			'mastersthesis': 'Master\'s Thesis',
			'phdthesis': 'PhD Thesis',
			'techreport': 'Technical Report',
			'misc': 'Miscellaneous'
		};
		return labels[type] || type;
	}
}

// Export for use in other scripts
window.BibtexParser = BibtexParser;
