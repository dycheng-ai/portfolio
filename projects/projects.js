import { fetchJSON, renderProjects } from '../global.js';
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm';

const projects = await fetchJSON('../lib/projects.json');
const projectsContainer = document.querySelector('.projects');
const searchInput = document.querySelector('.searchBar');

let query = '';
let selectedIndex = -1;

function renderPieChart(projectsGiven) {
  let newRolledData = d3.rollups(
    projectsGiven,
    (v) => v.length,
    (d) => d.year,
  );
  let newData = newRolledData.map(([year, count]) => {
    return { value: count, label: year };
  });

  let arcGenerator = d3.arc().innerRadius(0).outerRadius(50);
  let newSliceGenerator = d3.pie().value((d) => d.value);
  let newArcData = newSliceGenerator(newData);
  let newArcs = newArcData.map((d) => arcGenerator(d));
  let colors = d3.scaleOrdinal(d3.schemeTableau10);

  let svg = d3.select('svg');
  svg.selectAll('path').remove();

  let legend = d3.select('.legend');
  legend.selectAll('li').remove();

  newArcs.forEach((arc, i) => {
    svg
      .append('path')
      .attr('d', arc)
      .attr('fill', colors(i))
      .attr('class', selectedIndex === i ? 'selected' : '')
      .on('click', () => {
        selectedIndex = selectedIndex === i ? -1 : i;

        svg
          .selectAll('path')
          .attr('class', (_, idx) => (idx === selectedIndex ? 'selected' : ''));

        legend
          .selectAll('li')
          .attr('class', (_, idx) =>
            idx === selectedIndex ? 'legend-item selected' : 'legend-item'
          );

        if (selectedIndex === -1) {
          renderProjects(projects, projectsContainer, 'h2');
        } else {
          let selectedYear = newData[selectedIndex].label;
          let filtered = projects.filter((p) => String(p.year) === String(selectedYear));
          renderProjects(filtered, projectsContainer, 'h2');
        }
      });
  });

  newData.forEach((d, idx) => {
    legend
      .append('li')
      .attr('class', idx === selectedIndex ? 'legend-item selected' : 'legend-item')
      .attr('style', `--color:${colors(idx)}`)
      .html(`<span class="swatch"></span> ${d.label} <em>(${d.value})</em>`);
  });
}

renderProjects(projects, projectsContainer, 'h2');
renderPieChart(projects);

searchInput.addEventListener('input', (event) => {
  query = event.target.value;
  let filteredProjects = projects.filter((project) => {
    let values = Object.values(project).join('\n').toLowerCase();
    return values.includes(query.toLowerCase());
  });
  renderProjects(filteredProjects, projectsContainer, 'h2');
  renderPieChart(filteredProjects);
});
