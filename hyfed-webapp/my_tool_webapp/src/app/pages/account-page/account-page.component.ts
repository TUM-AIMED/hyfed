import { Component, OnInit } from '@angular/core';
import { UserService } from '../../services/user.service';
import { ActivatedRoute, Router } from '@angular/router';

type Page = 'ACCOUNT' | 'SIGNUP' | 'LOGIN' | 'LOGOUT';

@Component({
  selector: 'app-account-page',
  templateUrl: './account-page.component.html',
  styleUrls: ['./account-page.component.scss']
})
export class AccountPageComponent implements OnInit {

  private static PAGE_NAMES: { [page in Page]: string } = {
    ACCOUNT: 'Account',
    SIGNUP: 'Sign up',
    LOGIN: 'Log in',
    LOGOUT: 'Log out',
  };

  private queryP: string | null = null;

  public appMessage = '';

  public user = null;
  public page: Page;
  public pageName: string;
  public step = 1;

  // Login
  public loginUsername: string;
  public loginPassword: string;

  // Signup
  public signupUsername: string;
  public signupPassword: string;
  public confirmPassword: string;

  constructor(private route: ActivatedRoute, private router: Router, public users: UserService) {
    this.users.subscribeUser((user) => {
      this.user = user;
      this.updatePage();
    });
  }

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.queryP = params.p || null;
      this.updatePage();
    });
  }

  private updatePage() {

    // Signup request
    if (!this.user && !this.queryP){
        this.appMessage = `Please choose a username and password:`;
        this.setPage('SIGNUP');
        return
    }

    // login request
    if (!this.user && this.queryP === 'login'){
        this.appMessage = `Please enter the username and password:`;
        this.setPage('LOGIN');
        return
    }

    // logout request
    if (this.user && this.queryP === 'logout'){
       this.appMessage = `Please confirm logout by clicking on the 'Log out' button below.`;
       this.setPage('LOGOUT');
       return
    }

    // logout confirm request
    if (!this.user && this.queryP === 'logout'){
        this.router.navigate(['']);
        return
    }

    // login completed
    if (this.user && this.queryP === 'login'){
        this.router.navigate(['projects']);
        return
    }

    this.appMessage = `Hello, ${this.user.username}`
    this.setPage('ACCOUNT');
  }

  public async login() {
    this.appMessage = `Looking for your account...`;
    const result = await this.users.login(this.loginUsername, this.loginPassword);
    if (!result.result) {
      this.appMessage = result.message;
    }
  }

  public async signup() {
    if (this.signupUsername.length < 6) {
      this.appMessage = `The username should be at least 6 characters long.`;
      return;
    }

    if (this.signupPassword.length < 8) {
      this.appMessage = `The password should be at least 8 characters long.`;
      return;
    }

    if (this.signupPassword !== this.confirmPassword) {
      this.appMessage = `The passwords do not match.`;
      return;
    }

    this.appMessage = `Thank you! Your account is being created, please wait a second...`;
    const result = await this.users.signup(this.signupUsername, this.signupPassword);
  }

  public async logout() {
    await this.users.logout();
    this.router.navigate(['/']);
  }

  private setPage(page: Page) {
    this.page = page;
    this.pageName = AccountPageComponent.PAGE_NAMES[page];
  }

}
