import {BaseModel, IModelJson} from './base.model';

type ToolType = 'Select' | 'Stats'; // ADD THE TOOL NAME(S) HERE
type AlgorithmType = 'Select' | 'Variance' | 'Logistic-Regression'; // ADD THE ALGORITHM NAME(S) HERE

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

  // BEGIN Stats TOOL SPECIFIC ATTRIBUTES
  features?: string;
  learning_rate?: number;
  max_iterations?: number;
  // END Stats TOOL SPECIFIC ATTRIBUTES

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

  // BEGIN Stats TOOL SPECIFIC ATTRIBUTES
  private _features: string;
  private _learningRate: number;
  private _maxIterations: number;
  // END Stats TOOL SPECIFIC ATTRIBUTES

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

    // BEGIN Stats TOOL SPECIFIC ATTRIBUTES
    this._features = proj.features
    this._learningRate = proj.learning_rate
    this._maxIterations = proj.max_iterations
    // END Stats TOOL SPECIFIC ATTRIBUTES

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

  // BEGIN Stats TOOL SPECIFIC ATTRIBUTES
  public get features(): string {
    return this._features
  }

  public get learningRate(): number {
    return this._learningRate;
  }

  public get maxIterations(): number {
    return this._maxIterations;
  }
  // END Stats TOOL SPECIFIC ATTRIBUTES


}
