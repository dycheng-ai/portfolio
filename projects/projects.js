import { fetchJSON, renderProjects } from '../global.js';

const projects = await fetchJSON('../lib/projects.json');
console.log(projects);
const projectsContainer = document.querySelector('.projects');
try {
    if (projects.length == 0){
        projectsContainer.innerHTML = '<p>No projects to display at the moment. Please check back later!</p>';
    } else {
        renderProjects(projects, projectsContainer, 'h2');
    }
} catch (error) {
  console.error('Error rendering projects:', error);
  projectsContainer.innerHTML = '<p>Sorry, we couldn\'t display the projects right now.</p>';
}
