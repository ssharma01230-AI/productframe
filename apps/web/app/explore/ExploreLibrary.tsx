'use client';

import Image from 'next/image';
import { useMemo, useState } from 'react';
import { getEcommerceTemplateRecipes, type OutputRecipe } from '../studio/output-recipes';
import LibraryShell from '../products/LibraryShell';
import '../products/product-library.css';
import './explore.css';

type Props = { userId: string | null };
type Template = OutputRecipe & { categoryName: string; family: string };

const FAMILY_NAMES = ['t-shirts-casual-tops', 'sleeveless-tops', 'gilets-padded-vests', 'structured_bottoms', 'casual_bottoms', 'shirts', 'knitwear', 'hoodies', 'shorts', 'joggers', 'leggings', 'skirts', 'heels', 'boots', 'coats'];

const FALLBACK_FAMILIES: Record<string, string> = {
  tops: 't-shirts-casual-tops',
  bottoms: 'casual_bottoms',
  outerwear: 'jackets',
  footwear: 'shoes',
  socks: 'socks',
  underwear: 'underwear',
};

function templateFamily(id: string, categoryName: string) {
  const remainder = id.replace(`ecommerce-${categoryName}-`, '');
  const family = FAMILY_NAMES.find(candidate => remainder.startsWith(`${candidate}-`));
  return family ?? FALLBACK_FAMILIES[categoryName] ?? 'Other';
}

const templates: Template[] = getEcommerceTemplateRecipes()
  .filter(recipe => recipe.exampleImage.startsWith('/output-examples/'))
  .map(recipe => {
    const parts = recipe.id.replace(/^ecommerce-/, '').split('-');
    const categoryName = parts.shift() ?? 'Other';
    return { ...recipe, categoryName, family: templateFamily(recipe.id, categoryName) };
  });

const title = (value: string) => value === 'Core templates' ? value : value.replaceAll('_', '-').split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

export default function ExploreLibrary({ userId }: Props) {
  const [category, setCategory] = useState('All categories');
  const [family, setFamily] = useState('All families');
  const [query, setQuery] = useState('');
  const categories = [...new Set(templates.map(template => template.categoryName))];
  const families = [...new Set(templates.filter(template => category === 'All categories' || template.categoryName === category).map(template => template.family))];
  const visible = useMemo(() => templates.filter(template => {
    const matchesCategory = category === 'All categories' || template.categoryName === category;
    const matchesFamily = family === 'All families' || template.family === family;
    const haystack = `${template.name} ${template.description} ${template.family}`.toLowerCase();
    return matchesCategory && matchesFamily && haystack.includes(query.toLowerCase().trim());
  }), [category, family, query]);
  const categoryGroups = [...new Set(visible.map(template => template.categoryName))].map(categoryName => ({
    categoryName,
    families: [...new Set(visible.filter(template => template.categoryName === categoryName).map(template => template.family))],
  }));

  return <LibraryShell userId={userId} breadcrumb="Explore" active="explore">
    <header className="ex-header">
      <div><p className="pl-eyebrow">ECOMMERCE TEMPLATE LIBRARY</p><h1 className="pl-title">Explore</h1><p className="pl-subtitle">A visual library of every ecommerce example currently available. Browse by category, product family and product view.</p></div>
      <span className="pl-stat"><b>{templates.length}</b> templates</span>
    </header>
    <div className="ex-toolbar">
      <label className="ex-search"><span>Search templates</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search by product or view…" /></label>
      <label className="pl-sort"><span>Category</span><select value={category} onChange={event => { setCategory(event.target.value); setFamily('All families'); }}><option>All categories</option>{categories.map(value => <option value={value} key={value}>{title(value)}</option>)}</select></label>
    </div>
    <div className="ex-family-filter" aria-label="Filter by product family"><span>Families</span><div><button type="button" className={family === 'All families' ? 'is-active' : ''} onClick={() => setFamily('All families')}>All families</button>{families.map(value => <button type="button" className={family === value ? 'is-active' : ''} key={value} onClick={() => setFamily(value)}>{title(value)}</button>)}</div></div>
    <p className="ex-result-count">Showing {visible.length} of {templates.length} templates <span>· Ecommerce only · visual references available</span></p>
    <div className="ex-groups">
      {categoryGroups.map(({ categoryName, families }) => <section className="ex-category" key={categoryName}>
        <header className="ex-category-header"><h2>{title(categoryName)}</h2><span>{visible.filter(template => template.categoryName === categoryName).length} templates</span></header>
        {families.map(family => { const items = visible.filter(template => template.categoryName === categoryName && template.family === family); return <div className="ex-family" key={`${categoryName}/${family}`}>
          <header className="ex-family-header"><h3>{title(family)}</h3><span>{items.length} views</span></header>
          <div className="ex-grid">{items.map(template => <article className="ex-card" key={template.id}><div className="ex-image"><Image src={template.exampleImage} alt="" fill sizes="(max-width: 700px) 92vw, (max-width: 1100px) 30vw, 220px" unoptimized/><span>{template.presentation === 'worn_product' ? 'Worn product' : 'Product view'}</span></div><div className="ex-copy"><h3>{template.name}</h3><p>{template.description}</p></div></article>)}</div>
        </div>; })}
      </section>)}
    </div>
    {!visible.length && <div className="pl-empty"><h2>No templates found</h2><p>Try a different search or category.</p></div>}
  </LibraryShell>;
}
