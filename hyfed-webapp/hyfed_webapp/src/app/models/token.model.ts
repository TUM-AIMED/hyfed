/**
    Token model containing the token, username, and role(s) of the participant corresponding to the token

    Copyright 2021 Julian Matschinske and Reza NasiriGerdeh. All Rights Reserved.

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

import { BaseModel, IModelJson } from './base.model';

export interface TokenJson extends IModelJson {
  username: string;
  roles?: string[];
}

export class TokenModel extends BaseModel<TokenJson> {
  private _username: string;
  private _roles: string[];

  constructor() {
    super();
  }

  public async refresh(token: TokenJson) {
    this._id = token.id;
    this._username = token.username
    this._roles = token.roles;
  }

  public get username(): string {
    return this._username;
  }

  public get roles(): string[] {
    return this._roles;
  }
}
