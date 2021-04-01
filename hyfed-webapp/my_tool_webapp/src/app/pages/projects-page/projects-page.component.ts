import { Component, OnInit } from '@angular/core';
import { ProjectJson, ProjectModel } from '../../models/project.model';
import { ProjectService } from '../../services/project.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-projects-page',
  templateUrl: './projects-page.component.html',
  styleUrls: ['./projects-page.component.scss']
})
export class ProjectsPageComponent implements OnInit {

  public projects: ProjectModel[] = [];
  public newProject: ProjectJson = {
    tool: 'Select',
    algorithm: 'Select',
    name: '',
    description: '',
  };

  constructor(private router: Router, private projectService: ProjectService) {
    this.resetNewProject();
  }

  async ngOnInit() {
    await this.refreshProjects();
  }

  public async createProject() {
    const project = await this.projectService.createProject(this.newProject);
    this.resetNewProject();
    await this.router.navigate(['/project', project.id]);
  }

  public async deleteProject(project: ProjectModel) {
    await this.projectService.deleteProject(project);
    await this.refreshProjects();
  }

  public haveRole(project: ProjectModel, role: string): boolean {
    if (!project) {
      return false;
    }
    return project.roles.indexOf(role) !== -1;
  }


  private async refreshProjects() {
    this.projects = await this.projectService.getProjects();
  }

  private resetNewProject() {
    this.newProject.tool = 'Select';
    this.newProject.algorithm = 'Select';
    this.newProject.name = '';
    this.newProject.description = '';
  }

}
