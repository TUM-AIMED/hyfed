/**
    Copyright 2021 Julian Matschinske. All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
*/

import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ProjectJson, ProjectModel } from '../models/project.model';
import { TokenJson, TokenModel } from '../models/token.model';


@Injectable({
  providedIn: 'root'
})
export class ProjectService {

  constructor(private api: ApiService) {
  }

  public async getProjects(): Promise<ProjectModel[]> {
    return await this.api.get<ProjectJson[]>(`/projects/`).then(async (json) => {
      return await Promise.all(json.map(j => this.projectFromJson(j)));
    });
  }

  public async getProject(projId: string): Promise<ProjectModel | null> {
    return await this.api.get<ProjectJson>(`/projects/${projId}/`).then((json) => {
      return this.projectFromJson(json);
    }).catch((() => {
      return null;
    }));
  }

  public async createProject(proj: ProjectJson): Promise<ProjectModel> {
    return await this.api.post<ProjectJson>(`/projects/`, proj).then(async (json) => {
      return await this.projectFromJson(json);
    });
  }

  public async deleteProject(proj: ProjectModel): Promise<void> {
    await this.api.delete<ProjectJson>(`/projects/${proj.id}/`);
  }

  public async getTokens(proj: ProjectModel): Promise<TokenModel[]> {
    return await this.api.get<TokenJson[]>(`/projects/${proj.id}/tokens/`).then(async (json) => {
      return await Promise.all(json.map(j => this.tokenFromJson(j)));
    });
  }


  public async createToken(proj: ProjectModel): Promise<TokenModel> {
    return await this.api.post<TokenJson>(`/projects/${proj.id}/create_token/`, {}).then(async (json) => {
      return await this.tokenFromJson(json);
    });
  }

  public async deleteToken(token: TokenModel): Promise<void> {
    await this.api.delete<ProjectJson>(`/tokens/${token.id}/`);
  }

  public async projectFromJson(json: ProjectJson): Promise<ProjectModel> {
    const obj = new ProjectModel();
    await obj.refresh(json);
    return obj;
  }

  public async tokenFromJson(json: TokenJson): Promise<TokenModel> {
    const obj = new TokenModel();
    await obj.refresh(json);
    return obj;
  }

}
