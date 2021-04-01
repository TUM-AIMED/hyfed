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

import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { AccountPageComponent } from './pages/account-page/account-page.component';
import { PageNotFoundComponent } from './pages/page-not-found/page-not-found.component';
import { IndexPageComponent } from './pages/index-page/index-page.component';
import { ProjectsPageComponent } from './pages/projects-page/projects-page.component';
import { ProjectPageComponent } from './pages/project-page/project-page.component';
import { HowToPageComponent } from './pages/how-to-page/how-to-page.component';
import {AboutPageComponent} from './pages/about-page/about-page.component';

const routes: Routes = [
  { path: '', component: IndexPageComponent },
  { path: 'account', component: AccountPageComponent },
  { path: 'projects', component: ProjectsPageComponent },
  { path: 'how-to', component: HowToPageComponent },
  { path: 'about', component: AboutPageComponent },
  { path: 'project/:project_id', component: ProjectPageComponent },
  { path: '**', component: PageNotFoundComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
