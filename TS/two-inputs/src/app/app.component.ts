import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { MatInputModule } from '@angular/material/input';
import {MatButtonModule} from '@angular/material/button';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, MatInputModule, FormsModule, MatButtonModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  inputOne: number | null = null;  // Default initialization to 50
  inputTwo: number | null = null;  // Default initialization to 50
  min: number | null = 100;
  max: number | null = 250;
  step: number | null = 25;
  targetValue: number | null = 325;
  indexOne: number = 0;
  indexTwo: number = 0;
  possibleValues: Array<[number, number]> | null = [];

  constructor() {
    this.possibleValues = AppComponent.findValidPairs(this.step, this.min, this.max, this.targetValue);
  }

  ngOnInit() {
    this.possibleValues = AppComponent.findValidPairs(this.step, this.min, this.max, this.targetValue);
  }

  public updateInput() {
    this.possibleValues = AppComponent.findValidPairs(this.step, this.min, this.max, this.targetValue);
  }

  private changeIndex(currentValue: number, direction: boolean) {
    this.possibleValues = AppComponent.findValidPairs(this.step, this.min, this.max, this.targetValue);
    const length = this.possibleValues?.length;
    if(typeof length !== "undefined") {
    if(direction) {
      if(currentValue + 1 > length - 1) {
        return 0;
      }
      return currentValue + 1;
    } else {
      if(currentValue - 1 < 0) {
        return length - 1;
      }
      return currentValue - 1;
    }
    } else {
      console.error(`appComponent, changeIndex, length is undefined!`, length);
    }
    return currentValue;
  }

  updateTwoValue() {
    if(this.possibleValues !== null) {
      this.inputOne = this.possibleValues[this.indexOne][0];
      if(typeof this.inputOne !== "undefined" && this.inputOne !== null) {
      const result = AppComponent.findCorrespondingValue(this.possibleValues, this.inputOne);
      if(result !== null) {
        [this.inputTwo, this.indexTwo] = result;
        return;
      }
      console.error(`result is null!`);
    }
      console.error(`this.inputOne is null or undefined!: `, this.inputOne, this.possibleValues, this.indexOne);
    }
  }

  upOne() {
    this.indexOne = this.changeIndex(this.indexOne, true);
    this.updateTwoValue();
  }

  downOne() {
    this.indexOne = this.changeIndex(this.indexOne, false);
    this.updateTwoValue();
  }

  upTwo() {
    this.indexTwo = this.changeIndex(this.indexTwo, true);
    if(this.possibleValues !== null) {
      this.inputTwo = this.possibleValues[this.indexTwo][1];
      const result = AppComponent.findCorrespondingValue(this.possibleValues, this.inputTwo);
      if(result !== null) {
        [this.inputOne, this.indexOne] = result;
      }
    }
  }

  downTwo() {
    this.indexTwo = this.changeIndex(this.indexTwo, false);
    if(this.possibleValues !== null) {
      this.inputTwo = this.possibleValues[this.indexTwo][1];
      const result = AppComponent.findCorrespondingValue(this.possibleValues, this.inputTwo);
      if(result !== null) {
        [this.inputOne, this.indexOne] = result;
      }
    }
  }

  private static findCorrespondingValue(pairs: Array<[number, number]>, number: number): [number, number] | null {
    for (let index = 0; index < pairs.length; index += 1) {
        if (pairs[index][0] === number) {
            return [pairs[index][1], index]; // Return n2 if the given number matches n1
        } else if (pairs[index][1] === number) {
            return [pairs[index][0], index]; // Return n1 if the given number matches n2
        }
    }
    console.error("No corresponding value found for the provided number in the pairs.", pairs, number);
    return null; // Return null if no matching number is found
}

  private static findValidPairs(x: number | null, y: number | null, z: number | null, ml: number | null): Array<[number, number]> | null {
    if (x === null || y === null || z === null || ml === null) {
        console.error("findValidPairs, some value is null");
        return null;
    }

    const results: Array<[number, number]> = [];

    // Iterate through possible values of n1, which must be multiples of x, at least y, and not more than z
    for (let n1 = y; n1 <= ml - y && n1 <= z; n1 += x) {
        const n2 = ml - n1;
        // Ensure n2 is also a multiple of x, n2 >= y, and n2 <= z
        if (n2 % x === 0 && n2 >= y && n2 <= z) {
            results.push([n1, n2]);
        }
    }

    return results;
}

}
