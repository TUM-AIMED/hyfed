/**
    Model containing the attributes of the user such as username, and email address

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

import {BaseModel, IModelJson} from './base.model';

export interface UserJson extends IModelJson {

  username: string;
  first_name: string;
  last_name: string;
  email: string;
}

export class UserModel extends BaseModel<UserJson> {

  private _username: string;
  private _firstName: string;
  private _lastName: string;
  private _email: string;

  constructor() {
    super();
  }

  public async refresh(user: UserJson) {
    this._id = user.id;
    this._username = user.username;
    this._firstName = user.first_name;
    this._lastName = user.last_name;
    this._email = user.email;
  }

  public get username(): string {
    return this._username;
  }

  public get firstName(): string {
    return this._firstName;
  }

    public get lastName(): string {
    return this._lastName;
  }

  public get email(): string {
    return this._email;
  }

}
