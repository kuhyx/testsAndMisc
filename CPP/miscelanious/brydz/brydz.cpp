#include <iostream>
#include <vector>

const std::vector<std::string> ATUTY = {"BA", "Trefl", "Karo", "Kier", "Pik"};
const bool A_ID = 0;
const bool B_ID = 1;
const std::vector<std::string> GRACZE = {"Gracz A", "Gracz B"};
const std::vector<std::string> PO_PARTII{"Nikt", GRACZE[A_ID], GRACZE[B_ID],
                                         "Obaj Gracze"};
const int DOMYSLNE_LEWY = 6;
const int BEZ_ATUTU_ID = 1;
const int TREFL_ID = 2;
const int KARO_ID = 3;
const int KIER_ID = 4;
const int PIK_ID = 5;
const int SZLEMIK = 6;
const int SZLEM = 7;
const int CYKL_PO_PARTII = 4;
const int MAKSYMALNY_LEW = 7;
const int MINIMALNY_LEW = 1;
const int ILOSC_LEW = 13;

void print(const std::string s) { std::cout << s << std::endl; }

void tabela(std::vector<int> punktyA, std::vector<int> punktyB) {

  std::cout << "Numer Gry" << "    Po Partii" << "          " << GRACZE[A_ID]
            << "    " << GRACZE[B_ID] << std::endl;
  for (int i = 0; i < punktyA.size(); i++) {

    std::cout << i + 1 << "            " << PO_PARTII[i % CYKL_PO_PARTII]
              << "               " << punktyA[i] << "                 "
              << punktyB[i] << std::endl;
  }
}

void lwyAtut(int lwy, int atut) {
  if (lwy == SZLEMIK) {
    print("Wybrano szlemik!");
    return;
  }
  if (lwy == SZLEM) {
    print("Wybrano szlema!");
    return;
  }
  std::cout << "Wybrano kontrakt: " << lwy << " " << ATUTY[atut - 1]
            << std::endl;
}

int zagraneLwy() {
  int lwy;
  bool flagaLwy;
  do {
    flagaLwy = 0;
    print("Ile lew?");
    char lwyC;
    std::cin >> lwyC;
    lwy = lwyC - '0';
    if (lwy < MINIMALNY_LEW) {
      print("Podales za malo lew!");
      flagaLwy = 1;
    }

    if (lwy > MAKSYMALNY_LEW) {
      print("Podales za duzo lew!");
      flagaLwy = 1;
    }
  } while (flagaLwy);
  return lwy;
}

int zagranyAtut(int lwy) {
  int atut;
  bool flagaAtut;
  if (lwy > 6)
    return 1;
  do {
    flagaAtut = 0;
    print("Jaki atut?");
    print("1 - BA");
    print("2 - Trefl");
    print("3 - Karo");
    print("4 - Kier");
    print("5 - Pik");
    char atutC;
    std::cin >> atutC;
    atut = atutC - '0';
    if (atut < 1 || atut > 5) {
      print("Wybrales zla liczbe!");
      flagaAtut = 1;
    }
  } while (flagaAtut);
  return atut;
}

bool zagranaKontra() {
  char kontraC = '0';
  print("Czy zostala zagrana kontra?");
  print("1 - TAK");
  print("0 - NIE");
  std::cin >> kontraC;
  bool kontraBool = kontraC - '0';
  return kontraBool;
}

bool zagranaRekontra() {
  char rekontraC = '0';
  print("Czy zostala zagrana rekontra?");
  print("1 - TAK");
  print("0 - NIE");
  std::cin >> rekontraC;
  bool rekontraBool = rekontraC - '0';
  return rekontraBool;
}

void stanGry(int lwy, int atut, bool kontraBool, bool rekontraBool,
             int ktoraGra, int ktoKontrakt) {
  std::cout << "Kontrakt Wygrali: " << GRACZE[ktoKontrakt] << std::endl;
  lwyAtut(lwy, atut);
  if (kontraBool) {
    if (rekontraBool)
      print("Zostala zagrana REkontra!");
    else
      print("Zostala zagrana Kontra!");
  }
  std::cout << "Po partii sa: " << PO_PARTII[ktoraGra % 4] << std::endl;
}

int ktoKontrakt() {
  char ktoKontraktC;
  print("Kto wygral Kontrakt?");
  std::cout << "1. " << GRACZE[A_ID] << std::endl;
  std::cout << "2. " << GRACZE[B_ID] << std::endl;
  std::cin >> ktoKontraktC;
  int ktoKontraktI = ktoKontraktC - '1';
  std::cout << "ktoKontraktI " << ktoKontraktI;
  return ktoKontraktI;
}

int ileWpadek() {
  std::string ileWpadekS;
  print("ile lew wygrali obroncy?");
  std::cin >> ileWpadekS;
  int ileWpadek = stoi(ileWpadekS);
  return ileWpadek;
}

void punkty(std::vector<int> &punktyA, std::vector<int> &punktyB, int lwy,
            int atut, bool kontraBool, bool rekontraBool, int ktoraGra,
            int ktoKontraktI, bool rozgrywajacyWygral, int wpadki) {
  int sumaPunktow = 0;
  if (rozgrywajacyWygral) {
    int zdobyteLewy = ILOSC_LEW - wpadki - DOMYSLNE_LEWY;
    int nadrobki = zdobyteLewy - lwy;
    int punktyZaLew;
    std::cout << "wartosc kontraBool: " << kontraBool
              << "; wartosc rekontraBool: " << rekontraBool << std::endl;

    // Lewy Deklarowane
    if (atut == TREFL_ID || atut == KARO_ID) {
      print("kontrakt TREFL lub KARO kazda karta kontraktowa za 20");
      punktyZaLew = 20;
      if (kontraBool) {
        print("kontra TREFL lub KARO, kazda karta kontraktowa za 40");
        punktyZaLew = 40;
      }
      if (rekontraBool) {
        print("rekontra TREFL lub KARO, kazda karta kontraktowa za 80");
        punktyZaLew = 80;
      }

      std::cout << "Ilosc lew w kontrakcie: " << lwy
                << " do punktow dodaje sie " << lwy * punktyZaLew << std::endl;
      sumaPunktow += (lwy * punktyZaLew);
    }

    if (atut == KIER_ID || atut == PIK_ID) {
      print("kontrakt KIER lub PIK, kazda kontraktowa 30");
      punktyZaLew = 30;
      if (kontraBool) {
        print("kontra KIER lub PIK, kazda kontraktowa za 60");
        punktyZaLew = 60;
      }
      if (rekontraBool) {
        print("rekontra KIER lub PIK, kazda kontraktowa za 120");
        punktyZaLew = 120;
      }

      std::cout << "Ilosc lew w kontrakcie: " << lwy
                << " do punktow dodaje sie " << lwy * punktyZaLew << std::endl;
      sumaPunktow += (lwy * punktyZaLew);
    }

    if (atut == BEZ_ATUTU_ID) {
      punktyZaLew = 30;
      print("kontrakt BEZ_ATUTU, pierwsza lewa za 40, kazda nastepna za 30");
      sumaPunktow = 40;
      if (kontraBool) {
        print("kontrakt BEZ_ATUTU, pierwsza lewa za 80, kazda nastepna za 60");
        sumaPunktow = 80;
        punktyZaLew = 60;
      }
      if (rekontraBool) {
        print(
            "kontrakt BEZ_ATUTU, pierwsza lewa za 160, kazda nastepna za 120");
        sumaPunktow = 160;
        punktyZaLew = 120;
      }
      sumaPunktow += ((lwy - 1) * punktyZaLew);
    }

    bool czyRozgrywajacyPoPartii =
        (((ktoraGra % CYKL_PO_PARTII) - 1) == ktoKontraktI ||
         ktoraGra % CYKL_PO_PARTII == 3);

    if (lwy == SZLEMIK) {
      if (czyRozgrywajacyPoPartii)
        sumaPunktow += 750;
      else
        sumaPunktow += 500;
    }

    if (lwy == SZLEM) {
      if (czyRozgrywajacyPoPartii)
        sumaPunktow += 1500;
      else
        sumaPunktow += 1000;
    }

    bool dograna = (sumaPunktow >= 100);
    if (dograna) {
      if (czyRozgrywajacyPoPartii)
        sumaPunktow += 500;
      else
        sumaPunktow += 300;
    } else
      sumaPunktow += 50;

    // Nadrobki

    if (!kontraBool && !rekontraBool) {
      int punktyZaNadrobki = punktyZaLew;
      sumaPunktow += nadrobki * punktyZaNadrobki;
    }
    if (kontraBool && !rekontraBool) {
      int punktyZaNadrobki = 100;
      if (czyRozgrywajacyPoPartii)
        punktyZaNadrobki = 200;
      sumaPunktow += nadrobki * punktyZaNadrobki;
    }

    if (kontraBool && rekontraBool) {

      int punktyZaNadrobki = 200;
      if (czyRozgrywajacyPoPartii)
        punktyZaNadrobki = 400;
      sumaPunktow += nadrobki * punktyZaNadrobki;
    }

    if (kontraBool && !rekontraBool)
      sumaPunktow += 50;

    if (kontraBool && rekontraBool)
      sumaPunktow += 100;
    std::cout << "Rozgrywajacy zdobyl: " << sumaPunktow << std::endl;
    if (ktoKontraktI == A_ID) {
      punktyA.push_back(sumaPunktow);
      punktyB.push_back(0);
    } else {
      punktyB.push_back(sumaPunktow);
      punktyA.push_back(0);
    }
    return;
  } else {
    int zebraneLewy = ILOSC_LEW - wpadki;
    int lewyWpadkowe = (lwy + DOMYSLNE_LEWY) - zebraneLewy;
    int sumaPunktow = 0;
    bool broniacyPoPartii =
        (((ktoraGra % CYKL_PO_PARTII) - 1) == !ktoKontraktI ||
         ktoraGra % CYKL_PO_PARTII == 3);
    if (broniacyPoPartii) {

      if (!kontraBool && !rekontraBool) {
        sumaPunktow = 100;
        for (int i = 1; i < lewyWpadkowe; i++) {
          if (i < 4)
            sumaPunktow += 100;
          else
            sumaPunktow += 0;
        }
      }

      if (kontraBool && !rekontraBool) {
        sumaPunktow = 200;
        for (int i = 1; i < lewyWpadkowe; i++) {
          if (i < 4)
            sumaPunktow += 300;
          else
            sumaPunktow += 0;
        }
      }

      if (kontraBool && rekontraBool) {
        sumaPunktow = 400;
        for (int i = 1; i < lewyWpadkowe; i++) {
          if (i < 4)
            sumaPunktow += 600;
          else
            sumaPunktow += 0;
        }
      }
    } else {
      if (!kontraBool && !rekontraBool) {
        sumaPunktow = 50;
        for (int i = 1; i < lewyWpadkowe; i++) {
          if (i < 4)
            sumaPunktow += 50;
          else
            sumaPunktow += 0;
        }
      }

      if (kontraBool && !rekontraBool) {
        sumaPunktow = 100;
        for (int i = 1; i < lewyWpadkowe; i++) {
          if (i < 4)
            sumaPunktow += 200;
          else
            sumaPunktow += 100;
        }
      }

      if (kontraBool && rekontraBool) {
        sumaPunktow = 200;
        for (int i = 1; i < lewyWpadkowe; i++) {
          if (i < 4)
            sumaPunktow += 400;
          else
            sumaPunktow += 200;
        }
      }
    }
    std::cout << "Broniacy zdobyli: " << sumaPunktow << std::endl;
    if (ktoKontraktI == A_ID) {
      punktyB.push_back(sumaPunktow);
      punktyA.push_back(0);
    } else {
      punktyA.push_back(sumaPunktow);
      punktyB.push_back(0);
    }
    return;
  }
}

bool gra() {
  bool koniecGry = 0;
  std::vector<int> punktyA;
  std::vector<int> punktyB;
  do {
    int ktoraGra = 0;
    tabela(punktyA, punktyB);
    int ktoKontraktI = ktoKontrakt();
    int lwy = zagraneLwy();
    int atut = zagranyAtut(lwy);
    bool kontraBool = zagranaKontra();
    bool rekontraBool = 0;
    if (kontraBool)
      rekontraBool = zagranaRekontra();
    stanGry(lwy, atut, kontraBool, rekontraBool, ktoraGra, ktoKontraktI);
    int wpadki = ileWpadek();
    int zebraneLewy = ILOSC_LEW - wpadki;

    bool rozgrywajacyWygral = 1;
    if (zebraneLewy >= lwy + DOMYSLNE_LEWY)
      rozgrywajacyWygral = 1;
    else
      rozgrywajacyWygral = 0;
    punkty(punktyA, punktyB, lwy, atut, kontraBool, rekontraBool, ktoraGra,
           ktoKontraktI, rozgrywajacyWygral, wpadki);
    print("Czy koniec gry? 1 - TAK, 0 - NIE");
    std::cin >> koniecGry;
  } while (!koniecGry);
  tabela(punktyA, punktyB);
  return 0;
}

int main() {
  while (gra())
    ;
  return 0;
}
