import {BaseModel, IModelJson} from './base.model';

type ToolType = 'Select' | 'HyFed'; // ADD THE TOOL NAME(S) HERE
type AlgorithmType = 'Select' | 'HyFed-Algorithm'; // ADD THE ALGORITHM NAME(S) HERE

type StatusType = 'Created' | 'Parameters Ready' | 'Aggregating' | 'Done' | 'Aborted' | 'Failed';

export interface ProjectJson extends IModelJson {

  // Attributes common among all project types (tools)
  tool: ToolType;
  algorithm: AlgorithmType;
  name: string;
  description: string;
  status?: StatusType;
  step?: string;
  comm_round?: number;
  roles?: string[];
  token?: string;
  created_at?: string;

}

export class ProjectModel extends BaseModel<ProjectJson> {

  private _tool: ToolType;
  private _algorithm: AlgorithmType;
  private _name: string;
  private _description: string;
  private _status: StatusType;
  private _step: string;
  private _commRound: number;
  private _roles: string[];
  private _createdAt: Date;

  constructor() {
    super();
  }

  public async refresh(proj: ProjectJson) {
    this._id = proj.id;
    this._tool = proj.tool;
    this._algorithm = proj.algorithm;
    this._name = proj.name;
    this._description = proj.description;
    this._status = proj.status;
    this._step = proj.step;
    this._commRound = proj.comm_round;
    this._roles = proj.roles;
    this._createdAt = new Date(proj.created_at);

  }

  public get tool(): ToolType {
    return this._tool;
  }

  public get algorithm(): AlgorithmType {
    return this._algorithm;
  }

  public get name(): string {
    return this._name;
  }

    public get description(): string {
    return this._description;
  }

  public get status(): StatusType {
    return this._status;
  }

  public get step(): string {
    return this._step;
  }

  public get commRound(): number {
    return this._commRound;
  }

  public get roles(): string[] {
    return this._roles;
  }

  public get createdAt(): Date {
    return this._createdAt;
  }

}
