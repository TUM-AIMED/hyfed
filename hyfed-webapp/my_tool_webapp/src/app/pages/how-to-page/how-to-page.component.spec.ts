import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { HowToPageComponent } from './how-to-page.component';

describe('HowToPageComponent', () => {
  let component: HowToPageComponent;
  let fixture: ComponentFixture<HowToPageComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ HowToPageComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(HowToPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
