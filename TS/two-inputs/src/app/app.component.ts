import { Component } from "@angular/core";
import { CommonModule } from "@angular/common";
import { RouterOutlet } from "@angular/router";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { FormsModule } from "@angular/forms";
import {
  findValidPairs,
  findCorrespondingValue,
  changeIndex,
} from "./pair-logic";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    MatInputModule,
    FormsModule,
    MatButtonModule,
  ],
  templateUrl: "./app.component.html",
  styleUrls: ["./app.component.scss"],
})
export class AppComponent {
  inputOne: number | null = null;
  inputTwo: number | null = null;
  min: number | null = 100;
  max: number | null = 250;
  step: number | null = 25;
  targetValue: number | null = 325;
  indexOne: number = 0;
  indexTwo: number = 0;
  possibleValues: Array<[number, number]> | null = [];

  constructor() {
    this.possibleValues = findValidPairs(
      this.step,
      this.min,
      this.max,
      this.targetValue,
    );
  }

  ngOnInit() {
    this.possibleValues = findValidPairs(
      this.step,
      this.min,
      this.max,
      this.targetValue,
    );
  }

  public updateInput() {
    this.possibleValues = findValidPairs(
      this.step,
      this.min,
      this.max,
      this.targetValue,
    );
  }

  private doChangeIndex(currentValue: number, direction: boolean) {
    this.possibleValues = findValidPairs(
      this.step,
      this.min,
      this.max,
      this.targetValue,
    );
    const length = this.possibleValues?.length;
    return changeIndex(currentValue, direction, length);
  }

  updateTwoValue() {
    if (this.possibleValues !== null) {
      this.inputOne = this.possibleValues[this.indexOne][0];
      if (typeof this.inputOne !== "undefined" && this.inputOne !== null) {
        const result = findCorrespondingValue(
          this.possibleValues,
          this.inputOne,
        );
        if (result !== null) {
          [this.inputTwo, this.indexTwo] = result;
          return;
        }
        console.error("result is null!");
      }
      console.error(
        "this.inputOne is null or undefined!: ",
        this.inputOne,
        this.possibleValues,
        this.indexOne,
      );
    }
  }

  upOne() {
    this.indexOne = this.doChangeIndex(this.indexOne, true);
    this.updateTwoValue();
  }

  downOne() {
    this.indexOne = this.doChangeIndex(this.indexOne, false);
    this.updateTwoValue();
  }

  upTwo() {
    this.indexTwo = this.doChangeIndex(this.indexTwo, true);
    if (this.possibleValues !== null) {
      this.inputTwo = this.possibleValues[this.indexTwo][1];
      const result = findCorrespondingValue(
        this.possibleValues,
        this.inputTwo,
      );
      if (result !== null) {
        [this.inputOne, this.indexOne] = result;
      }
    }
  }

  downTwo() {
    this.indexTwo = this.doChangeIndex(this.indexTwo, false);
    if (this.possibleValues !== null) {
      this.inputTwo = this.possibleValues[this.indexTwo][1];
      const result = findCorrespondingValue(
        this.possibleValues,
        this.inputTwo,
      );
      if (result !== null) {
        [this.inputOne, this.indexOne] = result;
      }
    }
  }
}
