import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { ProjectModel } from '../../models/project.model';

import { ProjectService} from '../../services/project.service';
import { TokenModel } from '../../models/token.model';
import { UserService } from '../../services/user.service';
import { UserModel } from '../../models/user.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-project-page',
  templateUrl: './project-page.component.html',
  styleUrls: ['./project-page.component.scss']
})
export class ProjectPageComponent implements OnInit, OnDestroy {

  public user: UserModel | null = null;
  public projectId: string | null = null;
  public project: ProjectModel | null = null;
  public tokens: TokenModel[] = null;

  private interval: any = null;
  private ts = 0;

  constructor(private projectService: ProjectService,
              private userService: UserService,
              private route: ActivatedRoute) {
    userService.subscribeUser(async (user) => {
      if (!user) {
        return;
      }
      this.user = user;
      await this.refresh();
    });

    this.route.params.subscribe(async (params) => {
      let projectId = params.project_id;
      if (!projectId) {
        return;
      }

      if (this.projectId !== projectId) {
        this.projectId = projectId;
      }

      await this.refresh();
    });
  }

  ngOnInit() {
    this.interval = setInterval(async () => {
      this.refresh();
    }, 300000);
  }

  ngOnDestroy() {
    if (this.interval) {
      clearInterval(this.interval);
    }
  }

  public async refresh() {
    if (this.projectId && this.user) {
      this.project = await this.projectService.getProject(this.projectId);
      if (this.haveRole('coordinator')) {
        await this.refreshTokens();
      }
      await this.refreshResults();
      this.ts = new Date().getTime();
    }
  }

  public haveRole(role: string): boolean {
    if (!this.project) {
      return false;
    }
    return this.project.roles.indexOf(role) !== -1;
  }

  public async createToken() {
    await this.projectService.createToken(this.project);
    await this.refreshTokens();
  }

  public async deleteToken(token: TokenModel) {
    await this.projectService.deleteToken(token);
    await this.refreshTokens();
  }

  public async refreshResults() {
    // TODO
  }

  private async refreshTokens() {
    this.tokens = await this.projectService.getTokens(this.project);
  }

  public get downloadLink(): string {
    return `${environment.apiUrl}/projects/${this.project.id}/download_results/`;
  }

  public get plotSrc(): string {
    return `${environment.apiUrl}/projects/${this.project.id}/plot/?${this.ts}`;
  }

  // based on https://stackoverflow.com/questions/49102724/angular-5-copy-to-clipboard
  copyId(id: string){
    const selBox = document.createElement('textarea');
    selBox.style.position = 'fixed';
    selBox.style.left = '0';
    selBox.style.top = '0';
    selBox.style.opacity = '0';
    selBox.value = id;
    document.body.appendChild(selBox);
    selBox.focus();
    selBox.select();
    document.execCommand('copy');
    document.body.removeChild(selBox);
  }
}
